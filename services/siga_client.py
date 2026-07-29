import logging

import requests

logger = logging.getLogger(__name__)

ENDPOINT_ALUNO = "/sigaAPI/alunoConsultar"
ENDPOINT_MATRICULA = "/sigaAPI/matriculaConsultar"
ENDPOINT_CURSO = "/sigaAPI/cursoConsultar"
ENDPOINT_COBRANCA_POR_CPF = "/sigaAPI/cobrancaConsultarPorCpf"

TIMEOUT_SEGUNDOS = 10


class AlunoNaoEncontrado(Exception):
    """CPF não encontrado na base do SIGA."""


class SigaAPIError(Exception):
    """Erro de configuração, autenticação ou comunicação com o SIGA."""


class SigaClient:
    def __init__(self, base_url: str, api_key: str):
        if not base_url or not api_key:
            raise SigaAPIError(
                "SIGA_BASE_URL e SIGA_API_KEY precisam estar configurados."
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    def _get(self, caminho: str, params: dict) -> dict:
        """
        GET genérico contra a API do SIGA. Levanta AlunoNaoEncontrado em
        404 e SigaAPIError em qualquer outra falha (auth, rate limit,
        conexão, JSON inválido ou "sucesso": false no corpo).
        """
        url = self.base_url + caminho
        try:
            resposta = requests.get(
                url, headers=self._headers(), params=params, timeout=TIMEOUT_SEGUNDOS
            )
        except requests.RequestException as exc:
            raise SigaAPIError(f"Falha de conexão com o SIGA: {exc}") from exc

        if resposta.status_code == 404:
            raise AlunoNaoEncontrado()
        if resposta.status_code in (401, 403):
            raise SigaAPIError("Chave de API do SIGA inválida, expirada ou sem permissão.")
        if resposta.status_code == 429:
            raise SigaAPIError("Limite de requisições do SIGA excedido. Tente novamente em instantes.")
        if not resposta.ok:
            raise SigaAPIError(f"SIGA retornou erro {resposta.status_code}: {resposta.text[:300]}")

        try:
            corpo = resposta.json()
        except ValueError as exc:
            raise SigaAPIError("Resposta do SIGA não é um JSON válido.") from exc

        if not corpo.get("sucesso"):
            raise SigaAPIError(corpo.get("mensagem") or "SIGA retornou uma falha não especificada.")

        return corpo.get("dados") or {}

    def buscar_aluno_por_cpf(self, cpf: str) -> dict:
        """
        Busca nome, curso, e-mail e telefone do aluno na API do SIGA a
        partir do CPF. Levanta AlunoNaoEncontrado se o CPF não constar
        na base, ou SigaAPIError em caso de falha de configuração,
        autenticação ou comunicação.

        Curso não vem no /alunoConsultar -- é buscado à parte via
        /matriculaConsultar (que devolve tb_curso_id) + /cursoConsultar
        (que devolve o nome). Se essa segunda etapa falhar por qualquer
        motivo, a busca não é interrompida: o aluno só entra sem curso
        pré-preenchido e digita manualmente na tela.
        """
        cpf_limpo = "".join(c for c in cpf if c.isdigit())
        if len(cpf_limpo) != 11:
            raise SigaAPIError("CPF inválido.")

        dados_aluno = self._get(ENDPOINT_ALUNO, {"cpf": cpf_limpo})
        if not dados_aluno:
            raise AlunoNaoEncontrado(cpf_limpo)

        cursos = self._buscar_cursos(cpf_limpo)

        return {
            "nome": dados_aluno.get("nome") or "",
            "cpf": cpf_limpo,
            # Lista de cursos em que o aluno está matriculado -- pode ter
            # mais de um item quando o aluno tem mais de uma matrícula.
            # Nesse caso a tela pede pra pessoa escolher de qual curso
            # está mandando a documentação (ver templates/upload.html).
            "cursos": cursos,
            "email": dados_aluno.get("email") or "",
            "telefone": dados_aluno.get("celular") or dados_aluno.get("telefone") or "",
        }

    def _buscar_cursos(self, cpf_limpo: str) -> list:
        """
        Devolve a lista de cursos (id + nome) em que o aluno está
        matriculado, sem repetição. Se a busca de matrículas ou de algum
        curso individual falhar, essa entrada é simplesmente pulada -- o
        aluno pode não ter curso pré-preenchido, mas a busca continua.
        """
        matriculas = self._buscar_matriculas(cpf_limpo)

        curso_ids = []
        for matricula in matriculas:
            curso_id = matricula.get("tb_curso_id")
            if curso_id and curso_id not in curso_ids:
                curso_ids.append(curso_id)

        if not curso_ids:
            logger.warning(
                "SIGA: não foi possível descobrir tb_curso_id para o CPF %s", cpf_limpo
            )
            return []

        cursos = []
        for curso_id in curso_ids:
            try:
                curso = self._get(ENDPOINT_CURSO, {"id": curso_id})
            except (AlunoNaoEncontrado, SigaAPIError) as exc:
                logger.warning(
                    "SIGA: cursoConsultar falhou para id=%s (cpf %s): %s",
                    curso_id, cpf_limpo, exc,
                )
                continue

            # cursoConsultar?id= costuma devolver um dict único; se algum
            # dia vier lista (ex.: filtro por nome), pega o primeiro item.
            if isinstance(curso, list):
                curso = curso[0] if curso else {}

            nome = curso.get("nome") or ""
            if nome:
                cursos.append({"id": curso_id, "nome": nome})
            else:
                logger.warning(
                    "SIGA: cursoConsultar?id=%s respondeu sem 'nome' (cpf %s): %r",
                    curso_id, cpf_limpo, curso,
                )

        return cursos

    def _buscar_matriculas(self, cpf_limpo: str) -> list:
        """
        Busca todas as matrículas do aluno, por dois caminhos, porque
        matriculaConsultar?cpf= sozinho pode não bastar (a doc do SIGA
        indica que cpf precisa vir acompanhado de tb_curso_id nesse
        endpoint):

        1) matriculaConsultar?cpf=  -- tentativa direta. Normalmente
           devolve um dict único, mas quando o aluno tem mais de uma
           matrícula pode devolver uma lista -- os dois formatos são
           aceitos aqui.
        2) cobrancaConsultarPorCpf?cpf= -- pega os tb_contrato_id de
           todas as cobranças do aluno (um por matrícula/contrato) e usa
           matriculaConsultar?id=<contrato> pra cada um.
        """
        matriculas = []
        try:
            resultado = self._get(ENDPOINT_MATRICULA, {"cpf": cpf_limpo})
            if isinstance(resultado, list):
                matriculas = [m for m in resultado if m]
            elif resultado:
                matriculas = [resultado]

            if not matriculas or not any(m.get("tb_curso_id") for m in matriculas):
                logger.info(
                    "SIGA: matriculaConsultar?cpf=%s respondeu sem tb_curso_id, "
                    "tentando via cobrancaConsultarPorCpf", cpf_limpo,
                )
                matriculas = []
        except (AlunoNaoEncontrado, SigaAPIError) as exc:
            logger.info(
                "SIGA: matriculaConsultar?cpf=%s falhou (%s), tentando via "
                "cobrancaConsultarPorCpf", cpf_limpo, exc,
            )

        if matriculas:
            return matriculas

        try:
            cobrancas = self._get(ENDPOINT_COBRANCA_POR_CPF, {"cpf": cpf_limpo})
        except (AlunoNaoEncontrado, SigaAPIError) as exc:
            logger.warning(
                "SIGA: cobrancaConsultarPorCpf?cpf=%s também falhou: %s",
                cpf_limpo, exc,
            )
            return []

        if isinstance(cobrancas, dict):
            cobrancas = [cobrancas]

        contrato_ids = []
        for cobranca in cobrancas or []:
            contrato_id = cobranca.get("tb_contrato_id")
            if contrato_id and contrato_id not in contrato_ids:
                contrato_ids.append(contrato_id)

        for contrato_id in contrato_ids:
            try:
                matricula = self._get(ENDPOINT_MATRICULA, {"id": contrato_id})
            except (AlunoNaoEncontrado, SigaAPIError) as exc:
                logger.warning(
                    "SIGA: matriculaConsultar?id=%s falhou (cpf %s): %s",
                    contrato_id, cpf_limpo, exc,
                )
                continue

            if isinstance(matricula, list):
                matriculas.extend(m for m in matricula if m)
            elif matricula:
                matriculas.append(matricula)

        return matriculas
