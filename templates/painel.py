<!DOCTYPE html>
<html lang="pt-BR">
<head>
<link rel="icon" type="image/png" href="{{ url_for('static', filename='logo-icone.png') }}">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Revisar - {{ aluno.nome }}</title>
<link href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --azul: #00609F; --azul-escuro: #063C63; --azul-fundo: #EAF3FA;
    --ambar: #F28B1F; --laranja: #E74926; --tinta: #10293D; --tinta-suave: #4C6478;
    --branco: #FFFFFF; --verde: #13A438; --verde-fundo: #E8F7EC;
    --vermelho: #E74926; --vermelho-fundo: #FDECEA; --raio: 16px;
    --sombra: 0 6px 20px rgba(6, 60, 99, 0.08);
  }
  * { box-sizing: border-box; }
  body {
    font-family: 'Inter', system-ui, sans-serif; margin: 0; min-height: 100vh;
    background: #F7FBFE; color: var(--tinta); padding: 20px 16px 100px;
  }
  .topo { max-width: 640px; margin: 0 auto 18px; }
  .voltar { color: var(--azul); font-size: 0.85rem; text-decoration: none; font-weight: 600; }
  h1 { font-family: 'Baloo 2', sans-serif; color: var(--azul-escuro); font-size: 1.4rem; margin: 10px 0 2px; }
  .subtitulo { color: var(--tinta-suave); font-size: 0.9rem; margin: 0; }

  .lista-docs { max-width: 640px; margin: 20px auto; display: flex; flex-direction: column; gap: 14px; }
  .doc-card { background: var(--branco); border-radius: var(--raio); box-shadow: var(--sombra); overflow: hidden; }
  .doc-card img { width: 100%; max-height: 340px; object-fit: contain; background: #eef4f8; display: block; }
  .doc-pdf {
    display: flex; align-items: center; gap: 10px; padding: 16px;
    background: #eef4f8; color: var(--azul-escuro); font-weight: 700;
    text-decoration: none; font-size: 0.95rem;
  }
  .doc-pdf svg { flex: none; width: 22px; height: 22px; }
  .doc-card .corpo { padding: 14px 16px; }
  .doc-card .doc-label { font-weight: 700; font-size: 0.95rem; }

  .doc-card.marcado { border: 2px solid var(--vermelho); }

  .doc-card.doc-card-pendencia {
    position: relative;
    border: 2px dashed var(--laranja);
  }
  .etiqueta-solicitado {
    position: absolute;
    top: 10px;
    left: 10px;
    z-index: 2;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--laranja);
    color: #fff;
    font-size: 0.66rem;
    font-weight: 800;
    letter-spacing: 0.05em;
    padding: 5px 11px 5px 9px;
    border-radius: 999px;
    box-shadow: 0 3px 10px rgba(231, 73, 38, 0.4);
    animation: pulso-etiqueta 1.8s ease-in-out infinite;
  }
  .etiqueta-solicitado svg { width: 12px; height: 12px; flex: none; }
  @keyframes pulso-etiqueta {
    0%, 100% { box-shadow: 0 3px 10px rgba(231, 73, 38, 0.4); }
    50% { box-shadow: 0 3px 16px rgba(231, 73, 38, 0.65); }
  }

  .toggle-ilegivel {
    display: flex; align-items: center; gap: 8px; margin-top: 10px; cursor: pointer;
    font-size: 0.85rem; font-weight: 600; color: var(--vermelho);
  }
  .campo-motivo {
    display: none; margin-top: 10px; width: 100%; padding: 10px 12px;
    border: 1.5px solid #F3C6BE; border-radius: 10px; font-family: inherit; font-size: 0.88rem;
    background: var(--vermelho-fundo);
  }
  .doc-card.marcado .campo-motivo { display: block; }

  .rodape-acoes {
    position: fixed; bottom: 0; left: 0; right: 0; background: var(--branco);
    box-shadow: 0 -4px 16px rgba(0,0,0,0.08); padding: 14px 16px calc(14px + env(safe-area-inset-bottom));
  }
  .rodape-acoes .conteudo { max-width: 640px; margin: 0 auto; display: flex; gap: 10px; }
  button {
    flex: 1; border: none; border-radius: 13px; padding: 14px; font-size: 0.95rem;
    font-weight: 700; font-family: inherit; cursor: pointer;
  }
  .btn-aprovar { background: linear-gradient(135deg, var(--verde), #0e8a2c); color: white; }
  .btn-reprovar { background: var(--vermelho-fundo); color: var(--vermelho); }
  button:disabled { opacity: 0.6; cursor: not-allowed; }

  .status-msg { max-width: 640px; margin: 10px auto 0; text-align: center; font-size: 0.88rem; font-weight: 600; }

  .aviso-pendencia {
    max-width: 640px; margin: 0 auto 20px; padding: 14px 16px; border-radius: 12px;
    background: var(--vermelho-fundo); color: var(--vermelho); font-size: 0.88rem; font-weight: 600;
  }
</style>
</head>
<body>

  <div class="topo">
    <a class="voltar" href="{{ url_for('painel.lista') }}">← Voltar</a>
    <h1>{{ aluno.nome }}</h1>
    <p class="subtitulo">{{ aluno.curso }} · CPF {{ aluno.cpf }} · enviado em {{ aluno.criado_em.strftime('%d/%m/%Y') }}</p>
  </div>

  {% if aguardando_reenvio %}
  <div class="aviso-pendencia">
    Pendência já enviada pra esse aluno -- aguardando ele reenviar os documentos marcados abaixo. A revisão libera de novo assim que ele reenviar.
  </div>
  {% endif %}

  <div class="lista-docs" id="lista-docs">
    {% for doc in documentos %}
    <div class="doc-card{% if aguardando_reenvio and doc.status == 'ilegivel' %} doc-card-pendencia{% endif %}" id="doc-{{ doc.id }}" data-doc-id="{{ doc.id }}">
      {% if aguardando_reenvio and doc.status == 'ilegivel' %}
      <span class="etiqueta-solicitado">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/></svg>
        DOCUMENTO SOLICITADO
      </span>
      {% endif %}
      {% if doc.eh_pdf %}
      <a class="doc-pdf" href="{{ url_for('painel.imagem_documento', aluno_id=aluno.id, documento_id=doc.id) }}" target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12m0-12 4 4m-4-4-4 4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>
        Abrir PDF em nova aba
      </a>
      {% else %}
      <img src="{{ url_for('painel.imagem_documento', aluno_id=aluno.id, documento_id=doc.id) }}" alt="{{ doc.tipo_documento }}">
      {% endif %}
      <div class="corpo">
        <div class="doc-label">{{ doc.label }}</div>
        {% if aguardando_reenvio %}
          {% if doc.status == "ilegivel" %}
          <label class="toggle-ilegivel" style="color:var(--vermelho);">Pendente: {{ doc.observacao or "sem motivo informado" }}</label>
          {% endif %}
        {% else %}
        <label class="toggle-ilegivel">
          <input type="checkbox" class="check-ilegivel">
          Marcar como pendente/ilegível
        </label>
        <textarea class="campo-motivo" rows="2" placeholder="Explique o que precisa ser reenviado (ex: RG cortado, comprovante vencido)"></textarea>
        {% endif %}
      </div>
    </div>
    {% endfor %}
  </div>

  <div class="rodape-acoes">
    <div class="conteudo">
      <button type="button" class="btn-reprovar" id="btn-reprovar">Enviar pendências</button>
      <button type="button" class="btn-aprovar" id="btn-aprovar">Aprovar documentação</button>
    </div>
    <div class="status-msg" id="status-msg"></div>
  </div>

<script>
const alunoId = {{ aluno.id }};

document.querySelectorAll('.check-ilegivel').forEach((chk) => {
  chk.addEventListener('change', () => {
    chk.closest('.doc-card').classList.toggle('marcado', chk.checked);
  });
});

const statusMsg = document.getElementById('status-msg');
const btnAprovar = document.getElementById('btn-aprovar');
const btnReprovar = document.getElementById('btn-reprovar');

btnAprovar.addEventListener('click', async () => {
  const marcados = document.querySelectorAll('.doc-card.marcado');
  if (marcados.length > 0) {
    statusMsg.style.color = '#c5221f';
    statusMsg.textContent = 'Você marcou documentos como pendentes -- use "Enviar pendências" em vez de aprovar.';
    return;
  }
  if (!confirm('Confirma que a documentação está completa e legível? Isso vai gerar o PDF final e subir pro Drive.')) return;

  btnAprovar.disabled = true;
  btnReprovar.disabled = true;
  statusMsg.style.color = '#4C6478';
  statusMsg.textContent = 'Gerando PDF e enviando pro Drive...';

  try {
    const resp = await fetch(`/painel/aluno/${alunoId}/aprovar`, { method: 'POST' });
    const resultado = await resp.json();
    if (resp.ok) {
      statusMsg.style.color = '#137333';
      statusMsg.textContent = 'Aprovado! Redirecionando...';
      setTimeout(() => { window.location.href = "{{ url_for('painel.lista') }}"; }, 1200);
    } else {
      statusMsg.style.color = '#c5221f';
      statusMsg.textContent = resultado.erro || 'Erro ao aprovar.';
      btnAprovar.disabled = false;
      btnReprovar.disabled = false;
    }
  } catch (e) {
    statusMsg.style.color = '#c5221f';
    statusMsg.textContent = 'Erro de conexão.';
    btnAprovar.disabled = false;
    btnReprovar.disabled = false;
  }
});

btnReprovar.addEventListener('click', async () => {
  const marcados = Array.from(document.querySelectorAll('.doc-card.marcado'));
  if (marcados.length === 0) {
    statusMsg.style.color = '#c5221f';
    statusMsg.textContent = 'Marque ao menos um documento como pendente/ilegível antes de enviar.';
    return;
  }

  const pendencias = [];
  for (const card of marcados) {
    const motivo = card.querySelector('.campo-motivo').value.trim();
    if (!motivo) {
      statusMsg.style.color = '#c5221f';
      statusMsg.textContent = 'Preencha o motivo de cada documento marcado.';
      return;
    }
    pendencias.push({ documento_id: Number(card.dataset.docId), motivo });
  }

  if (!confirm(`Confirma o envio de ${pendencias.length} pendência(s) para o aluno reenviar?`)) return;

  btnAprovar.disabled = true;
  btnReprovar.disabled = true;
  statusMsg.style.color = '#4C6478';
  statusMsg.textContent = 'Enviando...';

  try {
    const resp = await fetch(`/painel/aluno/${alunoId}/reprovar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pendencias }),
    });
    const resultado = await resp.json();
    if (resp.ok) {
      statusMsg.style.color = '#137333';
      statusMsg.textContent = 'Pendências registradas! Redirecionando...';
      setTimeout(() => { window.location.href = "{{ url_for('painel.lista') }}"; }, 1200);
    } else {
      statusMsg.style.color = '#c5221f';
      statusMsg.textContent = resultado.erro || 'Erro ao registrar pendências.';
      btnAprovar.disabled = false;
      btnReprovar.disabled = false;
    }
  } catch (e) {
    statusMsg.style.color = '#c5221f';
    statusMsg.textContent = 'Erro de conexão.';
    btnAprovar.disabled = false;
    btnReprovar.disabled = false;
  }
});
</script>

</body>
</html>
