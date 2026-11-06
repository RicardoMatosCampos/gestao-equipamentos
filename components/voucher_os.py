"""
voucher_os.py - Componente Oficial de Emissão, Assinatura Touch Mobile, WhatsApp e Impressão de Ordens de Serviço (OS)

Gera a folha formal de atendimento técnico, incluindo carimbos, assinaturas digitais,
quadro de assinatura por toque na tela do celular (HTML5 Canvas), compartilhamento via WhatsApp,
tabela de serviços, layout A4 pronto para impressão e botão de impressão direta no navegador.
"""

from typing import Dict, Any, Optional
import urllib.parse
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def gerar_link_whatsapp_os(os_row: Dict[str, Any]) -> str:
    """
    Gera um link direto do WhatsApp (wa.me) com o resumo formatado da Ordem de Serviço / Protocolo.
    """
    rid = os_row.get("id", "N/A")
    chamado = os_row.get("numero_chamado") or os_row.get("ticket") or "S/N"
    pedido = os_row.get("numero_pedido") or "Não informado"
    unidade = os_row.get("unidade_nome") or os_row.get("unidade") or "Unidade de Saúde"
    setor = os_row.get("setor_nome") or os_row.get("setor") or "Geral"
    equipamento = os_row.get("equipamento_nome") or os_row.get("item_solicitado") or "Equipamento TI"
    qtd = os_row.get("quantidade", 1)
    tecnico = os_row.get("tecnico_nome") or os_row.get("tecnico_responsavel") or "Equipe TI"
    status = os_row.get("status") or "Pendente"
    servico = os_row.get("servico_realizado") or os_row.get("motivo_chamado") or "Atendimento Técnico"

    texto = (
        f"*📋 PROTOCOLO DE ATENDIMENTO TI #{rid}*\n"
        f"• *Chamado:* {chamado}\n"
        f"• *Nº Pedido Estoque:* {pedido}\n"
        f"• *Unidade:* {unidade} ({setor})\n"
        f"• *Material:* {qtd}x {equipamento}\n"
        f"• *Serviço:* {servico}\n"
        f"• *Status:* {status}\n"
        f"• *Técnico:* {tecnico}"
    )
    return f"https://wa.me/?text={urllib.parse.quote(texto)}"


def gerar_termo_html(
    os_row: Dict[str, Any],
    assinatura_tec_b64: Optional[str] = None,
    assinatura_unidade_b64: Optional[str] = None,
    aplicar_sig_tec: bool = True,
    aplicar_sig_uni: bool = True,
    nome_resp_unidade: str = "Responsável pelo Posto / Unidade",
    cargo_resp_unidade: str = "Servidor Público • Recebimento"
) -> str:
    """
    Gera o bloco HTML do comprovante formal da Ordem de Serviço com assinaturas digitais.
    Responsivo para telas de celular e preservando layout A4 na impressão.
    """
    tecnico_nome_os = os_row.get('tecnico_nome', '')

    # Formatação de datas
    data_solic_fmt = ""
    if os_row.get("data"):
        try:
            data_solic_fmt = pd.to_datetime(os_row["data"]).strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_solic_fmt = str(os_row.get("data"))

    data_prev_fmt = ""
    if os_row.get("data_prevista_retorno"):
        try:
            data_prev_fmt = pd.to_datetime(os_row["data_prevista_retorno"]).strftime("%d/%m/%Y")
        except Exception:
            data_prev_fmt = str(os_row.get("data_prevista_retorno"))

    # Blocos visuais de assinatura digital formatados (com IDs para receber assinatura por toque na tela)
    if aplicar_sig_tec and assinatura_tec_b64:
        bloco_sig_tec = f'<div id="os-sig-tec-slot" style="min-height: 72px; height: 75px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 2px;"><img src="{assinatura_tec_b64}" style="max-height: 70px; max-width: 260px; object-fit: contain;" /></div>'
        selo_sig_tec = '<div id="os-selo-tec-slot" style="font-size: 0.65rem; color: #0284c7; font-weight: 700; margin-top: 3px;">🔒 Documento Assinado Digitalmente • Preposto TI</div>'
    else:
        bloco_sig_tec = '<div id="os-sig-tec-slot" style="min-height: 72px; height: 75px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 2px;"></div>'
        selo_sig_tec = '<div id="os-selo-tec-slot" style="font-size: 0.65rem; color: #0284c7; font-weight: 700; margin-top: 3px;"></div>'

    if aplicar_sig_uni and assinatura_unidade_b64:
        bloco_sig_uni = f'<div id="os-sig-uni-slot" style="min-height: 72px; height: 75px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 2px;"><img src="{assinatura_unidade_b64}" style="max-height: 70px; max-width: 260px; object-fit: contain;" /></div>'
        selo_sig_uni = '<div id="os-selo-uni-slot" style="font-size: 0.65rem; color: #16a34a; font-weight: 700; margin-top: 3px;">✅ Recebimento Validado na Unidade</div>'
    else:
        bloco_sig_uni = '<div id="os-sig-uni-slot" style="min-height: 72px; height: 75px; display: flex; align-items: flex-end; justify-content: center; margin-bottom: 2px;"></div>'
        selo_sig_uni = '<div id="os-selo-uni-slot" style="font-size: 0.65rem; color: #16a34a; font-weight: 700; margin-top: 3px;"></div>'

    pedido_txt = f" &bull; Nº Pedido Estoque: <strong>{os_row['numero_pedido']}</strong>" if os_row.get('numero_pedido') else ""

    return f"""<div class="gov-os-voucher" id="os-voucher-print">
<div class="os-header-flex" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #0f172a; padding-bottom: 12px; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
<div>
<div style="font-size: 0.75rem; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.05em;">ORDEM DE SERVIÇO &amp; TERMO DE ATENDIMENTO TI</div>
<div style="font-size: 1.25rem; font-weight: 800; color: #0f172a;">COMPROVANTE TÉCNICO #{os_row.get('id', 'N/A')}</div>
<div style="font-size: 0.8rem; color: #64748b;">Chamado / Ticket Oficial: <strong>{os_row.get('numero_chamado') or 'NÃO INFORMADO'}</strong>{pedido_txt}</div>
</div>
<div class="os-header-right" style="text-align: right; font-size: 0.8rem; color: #475569;">
<div><strong>Data de Abertura:</strong> {data_solic_fmt or 'Hoje'}</div>
<div><strong>Previsão de Retorno:</strong> {data_prev_fmt or 'Imediato'}</div>
<div><strong>Status:</strong> <span style="font-weight: 700;">{os_row.get('status', 'Pendente')}</span></div>
</div>
</div>
<table style="width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 0.85rem;">
<tr style="background: #f8fafc;">
<td style="padding: 8px 12px; border: 1px solid #cbd5e1; width: 50%;"><strong>Unidade de Saúde:</strong> {os_row.get('unidade_nome', 'N/A')}</td>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1; width: 50%;"><strong>Porte da Unidade:</strong> {os_row.get('porte', 'N/A')}</td>
</tr>
<tr>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Setor / Sala:</strong> {os_row.get('setor_nome', 'N/A')}</td>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Zona / Região:</strong> {os_row.get('zona', 'N/A')} | <strong>Lote:</strong> {os_row.get('empresa', 'N/A')}</td>
</tr>
<tr style="background: #f8fafc;">
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Técnico Responsável:</strong> {os_row.get('tecnico_nome', 'N/A')}</td>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Tipo de Visita:</strong> {os_row.get('tipo_visita', 'N/A')}</td>
</tr>
<tr>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Material / Equipamento:</strong> {os_row.get('equipamento_nome', 'N/A')}</td>
<td style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Quantidade Movimentada:</strong> {os_row.get('quantidade', 1)} unidade(s)</td>
</tr>
<tr style="background: #f8fafc;">
<td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Motivo do Chamado:</strong> {os_row.get('motivo_chamado', 'N/A')}</td>
</tr>
<tr>
<td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Serviço Realizado:</strong> {os_row.get('servico_realizado', 'N/A')}</td>
</tr>
<tr style="background: #f8fafc;">
<td colspan="2" style="padding: 8px 12px; border: 1px solid #cbd5e1;"><strong>Observações / Laudo Técnico:</strong> {os_row.get('observacao') or 'Sem observações adicionais.'}</td>
</tr>
</table>
<div class="os-signatures-flex" style="margin-top: 32px; display: flex; justify-content: space-between; gap: 40px; padding-top: 20px;">
<div style="flex: 1; text-align: center;">
{bloco_sig_tec}
<div style="border-top: 1.5px solid #334155; padding-top: 6px; font-size: 0.85rem; font-weight: 700; color: #0f172a;">{tecnico_nome_os or 'Técnico de TI'}</div>
<div style="font-size: 0.72rem; color: #64748b;">Técnico Responsável / Preposto TI</div>
{selo_sig_tec}
</div>
<div style="flex: 1; text-align: center;">
{bloco_sig_uni}
<div style="border-top: 1.5px solid #334155; padding-top: 6px; font-size: 0.85rem; font-weight: 700; color: #0f172a;">{nome_resp_unidade}</div>
<div style="font-size: 0.72rem; color: #64748b;">{cargo_resp_unidade} • {os_row.get('unidade_nome', 'Posto de Trabalho')}</div>
{selo_sig_uni}
</div>
</div>
</div>"""


def gerar_documento_html_completo(os_row: Dict[str, Any], termo_html: str) -> str:
    """
    Gera a página HTML completa formatada para layout folha A4 com suporte a impressão via CSS.
    """
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ordem de Serviço #{os_row.get('id', 'N/A')} - {os_row.get('unidade_nome', 'TI')}</title>
<style>
@page {{ size: A4 portrait; margin: 10mm 15mm; }}
* {{ box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background-color: #f8fafc;
    color: #0f172a;
    margin: 0;
    padding: 20px;
}}
.folha-a4 {{
    max-width: 860px;
    margin: 0 auto;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 24px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
}}
.barra-acoes {{
    max-width: 860px;
    margin: 0 auto 16px auto;
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}}
.btn-acao {{
    background: #0284c7;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 6px;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(2,132,199,0.3);
}}
.btn-acao:hover {{ background: #0369a1; }}
@media print {{
    body {{ background: #ffffff !important; padding: 0 !important; margin: 0 !important; }}
    .barra-acoes {{ display: none !important; }}
    .folha-a4 {{ border: none !important; box-shadow: none !important; padding: 0 !important; width: 100% !important; max-width: 100% !important; }}
}}
</style>
</head>
<body>
<div class="barra-acoes">
    <button class="btn-acao" onclick="window.print()">🖨️ Imprimir Agora (Ctrl + P)</button>
</div>
<div class="folha-a4">
{termo_html}
</div>
</body>
</html>"""


def render_quadro_assinatura_touch_os(id_alvo: Any) -> None:
    """
    Renderiza um Quadro de Assinatura na Tela por Toque (HTML5 Canvas) otimizado para celular e tablet.
    Permite assinar com o dedo/caneta e injetar a assinatura diretamente no comprovante de O.S. ou baixar o PNG.
    """
    html_canvas_touch = f"""
    <div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #f8fafc;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 0.85rem; font-weight: 700; color: #38bdf8;">✍️ Desenhe a Assinatura com o Dedo ou Mouse:</span>
            <select id="selDestinoAssinatura_{id_alvo}" style="background: #1e293b; color: #f8fafc; border: 1px solid #475569; border-radius: 6px; padding: 5px 10px; font-size: 0.82rem; font-weight: 600;">
                <option value="unidade">🏥 Recebedor na Unidade de Saúde (USF)</option>
                <option value="tecnico">👨‍💻 Técnico Responsável (Preposto TI)</option>
            </select>
        </div>
        <div style="background: #ffffff; border: 2px dashed #94a3b8; border-radius: 8px; overflow: hidden; touch-action: none;">
            <canvas id="canvasSigTouch_{id_alvo}" width="520" height="135" style="width: 100%; height: 135px; display: block; cursor: crosshair; touch-action: none;"></canvas>
        </div>
        <div style="display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap;">
            <button type="button" onclick="limparCanvas_{id_alvo}()" style="flex: 1; min-width: 110px; background: #334155; color: #e2e8f0; border: none; border-radius: 8px; padding: 9px 12px; font-size: 0.83rem; font-weight: 700; cursor: pointer;">
                🧹 Limpar Quadro
            </button>
            <button type="button" onclick="aplicarAssinaturaNaFolha_{id_alvo}()" style="flex: 2; min-width: 180px; background: linear-gradient(135deg, #0284c7, #2563eb); color: #ffffff; border: none; border-radius: 8px; padding: 9px 12px; font-size: 0.85rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 6px rgba(37, 99, 235, 0.35);">
                ✅ Aplicar na Folha da O.S. Agora
            </button>
            <button type="button" onclick="baixarPngAssinatura_{id_alvo}()" style="flex: 1; min-width: 130px; background: #0f766e; color: #ffffff; border: none; border-radius: 8px; padding: 9px 12px; font-size: 0.82rem; font-weight: 700; cursor: pointer;">
                💾 Baixar PNG
            </button>
        </div>
        <div id="msgStatusSig_{id_alvo}" style="font-size: 0.78rem; color: #4ade80; margin-top: 6px; min-height: 18px; font-weight: 600;"></div>
    </div>
    <script>
    (function() {{
        const canvas = document.getElementById('canvasSigTouch_{id_alvo}');
        const ctx = canvas.getContext('2d');
        let desenhando = false;
        let temTraco = false;

        function ajustarEscalaCanvas() {{
            const rect = canvas.getBoundingClientRect();
            if (rect.width > 0 && Math.abs(canvas.width - rect.width) > 20) {{
                canvas.width = rect.width;
                canvas.height = 135;
            }}
            ctx.strokeStyle = '#0f172a';
            ctx.lineWidth = 2.4;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        }}
        setTimeout(ajustarEscalaCanvas, 80);

        function obterPosicao(e) {{
            const rect = canvas.getBoundingClientRect();
            const clientX = e.touches ? e.touches[0].clientX : e.clientX;
            const clientY = e.touches ? e.touches[0].clientY : e.clientY;
            return {{
                x: (clientX - rect.left) * (canvas.width / rect.width),
                y: (clientY - rect.top) * (canvas.height / rect.height)
            }};
        }}

        function iniciar(e) {{
            e.preventDefault();
            desenhando = true;
            temTraco = true;
            const pos = obterPosicao(e);
            ctx.beginPath();
            ctx.moveTo(pos.x, pos.y);
        }}

        function mover(e) {{
            if (!desenhando) return;
            e.preventDefault();
            const pos = obterPosicao(e);
            ctx.lineTo(pos.x, pos.y);
            ctx.stroke();
        }}

        function parar(e) {{
            if (!desenhando) return;
            desenhando = false;
            ctx.closePath();
        }}

        canvas.addEventListener('mousedown', iniciar);
        canvas.addEventListener('mousemove', mover);
        window.addEventListener('mouseup', parar);
        canvas.addEventListener('touchstart', iniciar, {{ passive: false }});
        canvas.addEventListener('touchmove', mover, {{ passive: false }});
        canvas.addEventListener('touchend', parar);

        window.limparCanvas_{id_alvo} = function() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            temTraco = false;
            document.getElementById('msgStatusSig_{id_alvo}').textContent = 'Quadro limpo.';
        }};

        window.aplicarAssinaturaNaFolha_{id_alvo} = function() {{
            const msgEl = document.getElementById('msgStatusSig_{id_alvo}');
            if (!temTraco) {{
                msgEl.style.color = '#fbbf24';
                msgEl.textContent = '⚠️ Desenhe a assinatura no quadro branco antes de aplicar.';
                return;
            }}
            const dataUrl = canvas.toDataURL('image/png');
            const destino = document.getElementById('selDestinoAssinatura_{id_alvo}').value;
            const parentDoc = window.parent.document || document;
            const slotId = (destino === 'tecnico') ? 'os-sig-tec-slot' : 'os-sig-uni-slot';
            const seloId = (destino === 'tecnico') ? 'os-selo-tec-slot' : 'os-selo-uni-slot';
            const slotEl = parentDoc.getElementById(slotId);
            const seloEl = parentDoc.getElementById(seloId);

            if (slotEl) {{
                slotEl.innerHTML = '<img src="' + dataUrl + '" style="max-height: 70px; max-width: 260px; object-fit: contain;" />';
                if (seloEl) {{
                    seloEl.textContent = (destino === 'tecnico')
                        ? '✍️ Assinado na Tela Mobile • Preposto TI'
                        : '✅ Assinado na Tela pelo Recebedor da Unidade';
                }}
                msgEl.style.color = '#4ade80';
                msgEl.textContent = '✅ Assinatura aplicada com sucesso na Folha de O.S. acima! Agora basta clicar em Imprimir.';
            }} else {{
                msgEl.style.color = '#f87171';
                msgEl.textContent = '❌ Não foi possível localizar a folha de O.S. na página.';
            }}
        }};

        window.baixarPngAssinatura_{id_alvo} = function() {{
            if (!temTraco) return;
            const link = document.createElement('a');
            link.download = 'assinatura_os_{id_alvo}.png';
            link.href = canvas.toDataURL('image/png');
            link.click();
        }};
    }})();
    </script>
    """
    components.html(html_canvas_touch, height=255)


def render_acoes_impressao_voucher(os_row: Dict[str, Any], termo_html: str, id_alvo: Any) -> None:
    """
    Renderiza os botões de ação: download em HTML/PDF, impressão direta via JavaScript,
    compartilhamento por WhatsApp em 1 toque e assinatura na tela por toque (mobile).
    """
    nome_arq_limpo = f"comprovante_os_{os_row.get('id', 'N/A')}_{str(os_row.get('unidade_nome', 'TI')).replace(' ', '_')}.html"
    doc_html = gerar_documento_html_completo(os_row, termo_html)
    url_whatsapp = gerar_link_whatsapp_os(os_row)

    col_btn_print1, col_btn_print2, col_btn_wpp = st.columns(3)
    with col_btn_print1:
        st.download_button(
            label="📥 Baixar O.S. (.html / PDF)",
            data=doc_html.encode("utf-8"),
            file_name=nome_arq_limpo,
            mime="text/html",
            use_container_width=True,
            key=f"btn_download_os_{id_alvo}",
            help="Baixa o documento oficial formatado para abrir no navegador ou salvar diretamente como PDF."
        )

    with col_btn_print2:
        js_popup_impressao = f"""
        <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
            <button onclick="imprimirComprovanteDireto()" style="
                width: 100%;
                min-height: 42px;
                background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
                color: white;
                border: none;
                padding: 10px 14px;
                border-radius: 8px;
                font-size: 0.90rem;
                font-weight: 700;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                box-shadow: 0 2px 5px rgba(2, 132, 199, 0.3);
            ">
                🖨️ Imprimir O.S. Direto
            </button>
        </div>
        <script>
        function imprimirComprovanteDireto() {{
            try {{
                var el = window.parent.document.getElementById('os-voucher-print');
                if (!el) {{
                    window.parent.print();
                    return;
                }}
                var w = window.open('', '_blank', 'width=880,height=800');
                w.document.write('<!DOCTYPE html><html><head><title>Ordem de Serviço #{os_row.get('id', 'N/A')}</title>');
                w.document.write('<style>');
                w.document.write('@page {{ size: A4 portrait; margin: 10mm; }}');
                w.document.write('* {{ box-sizing: border-box; }}');
                w.document.write('body {{ font-family: -apple-system, BlinkMacSystemFont, \\"Segoe UI\\", Roboto, Arial, sans-serif; margin: 0; padding: 15px; background: #fff; color: #0f172a; }}');
                w.document.write('.gov-os-voucher {{ border: 1px solid #cbd5e1; border-radius: 8px; padding: 20px; }}');
                w.document.write('table {{ width: 100%; border-collapse: collapse; }}');
                w.document.write('td {{ border: 1px solid #cbd5e1; padding: 8px 12px; font-size: 0.85rem; }}');
                w.document.write('</style></head><body>');
                w.document.write(el.outerHTML);
                w.document.write('</body></html>');
                w.document.close();
                w.focus();
                setTimeout(function() {{ w.print(); }}, 250);
            }} catch (e) {{
                window.parent.print();
            }}
        }}
        </script>
        """
        components.html(js_popup_impressao, height=52)

    with col_btn_wpp:
        st.markdown(
            f'<a href="{url_whatsapp}" target="_blank" rel="noopener noreferrer" class="btn-whatsapp-os">'
            f'📲 Enviar Resumo no WhatsApp</a>',
            unsafe_allow_html=True
        )

    with st.expander("✍️ Assinar na Tela do Celular (Com o Dedo ou Caneta Touch)", expanded=False):
        st.caption("Se você estiver em campo na USF com o celular ou tablet, o recebedor da unidade ou o técnico pode assinar diretamente no quadro abaixo:")
        render_quadro_assinatura_touch_os(id_alvo)

    st.caption("💡 Dica: Você pode colher a assinatura com o dedo na tela acima, imprimir direto ou enviar o resumo da O.S. via WhatsApp.")
