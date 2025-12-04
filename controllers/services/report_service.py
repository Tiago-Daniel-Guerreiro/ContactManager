import os
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List
from dataclasses import dataclass


@dataclass
class SendReport:
    contact_name: str
    contact_phone: str
    status: str  # 'sucesso', 'erro'
    message: str
    timestamp: str
    message_type: str = 'geral'  # 'boas-vindas' ou 'geral'


class ReportService:    
    @staticmethod
    def generate_html_report(reports: List[SendReport], method: str, output_file: Path) -> bool:
        try:
            # Estatísticas gerais
            successful = sum(1 for r in reports if r.status == "sucesso")
            total = len(reports)
            
            # Estatísticas por tipo de mensagem
            welcome_reports = [r for r in reports if r.message_type == 'boas-vindas']
            general_reports = [r for r in reports if r.message_type == 'geral']
            
            welcome_success = sum(1 for r in welcome_reports if r.status == "sucesso")
            general_success = sum(1 for r in general_reports if r.status == "sucesso")
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Relatório de Envios - {method.upper()}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            max-width: 1200px;
            margin-left: auto;
            margin-right: auto;
        }}
        h1 {{ margin-bottom: 5px; }}
        .subtitle {{ color: #666; margin-top: 0; }}
        .summary {{
            margin: 20px 0;
        }}
        .summary p {{ margin: 8px 0; }}
        .success {{ color: green; }}
        .error {{ color: red; }}
        .note {{
            background: #fffbf0;
            padding: 15px;
            margin: 20px 0;
            border-left: 3px solid #ff9800;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th {{
            background: #333;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        tr:hover {{ background: #f5f5f5; }}
        .type-welcome {{ color: #9c27b0; font-weight: bold; }}
        .type-general {{ color: #2196f3; font-weight: bold; }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>Relatório de Envios</h1>
    <p class="subtitle">Método: {method.upper()} | Gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}</p>
    
    <div class="summary">
        <h2>Resumo</h2>
        <p><strong>Total de envios:</strong> {total}</p>
        <p class="success"><strong>Sucesso:</strong> {successful}/{total} ({(successful/total*100) if total > 0 else 0:.1f}%)</p>
        <p class="error"><strong>Erros:</strong> {total - successful}/{total}</p>
        <p><strong>Boas-vindas:</strong> {len(welcome_reports)} ({welcome_success} com sucesso)</p>
        <p><strong>Mensagens gerais:</strong> {len(general_reports)} ({general_success} com sucesso)</p>
    </div>
    
    <h2>Detalhes</h2>
    <table>
        <thead>
            <tr>
                <th>Nome</th>
                <th>Telefone</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Observação</th>
                <th>Data/Hora</th>
            </tr>
        </thead>
        <tbody>
"""
            
            for report in reports:
                status_text = "OK" if report.status == "sucesso" else "ERRO"
                status_class = "success" if report.status == "sucesso" else "error"
                
                type_class = "type-welcome" if report.message_type == 'boas-vindas' else "type-general"
                type_text = "Boas-vindas" if report.message_type == 'boas-vindas' else "Geral"
                
                html_content += f"""            <tr>
                <td>{report.contact_name}</td>
                <td>{report.contact_phone}</td>
                <td class="{type_class}">{type_text}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{report.message}</td>
                <td>{report.timestamp}</td>
            </tr>
"""
            
            html_content += """        </tbody>
    </table>
    
    <div class="footer">
        <p>Relatório gerado automaticamente</p>
    </div>
</body>
</html>
"""
            
            # Salva arquivo HTML
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
        except Exception as e:
            print(f"Erro ao gerar relatório: {e}")
            return False
    
    @staticmethod
    def open_report(report_file: Path, log_callback=None) -> bool:
        try:
            if os.name == 'nt':  # Windows
                os.startfile(str(report_file))
            else:  # Linux/Mac
                webbrowser.open(f'file://{report_file}')
            return True
        except Exception as e:
            if log_callback:
                log_callback(f"Não foi possível abrir relatório: {e}")
            return False
    
    @staticmethod
    def create_report_filename(method: str, base_dir: Path) -> Path:
        reports_dir = base_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"relatorio_{method}_{timestamp}.html"
        
        return report_file
