import os
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import List
from dataclasses import dataclass
from utils.logger import get_logger
from models.Result import Result, statusType, messageType

class ReportGenerator:
    
    @staticmethod
    def generate_statistics(reports: List[Result]) -> dict:
        stats = {
            "successful": 0,
            "invalid": 0,
            "errors": 0,
            "total": len(reports),
            "welcome_reports": 0,
            "general_reports": 0,
            "welcome_success": 0,
            "general_success": 0,
            "success_%": 0
        }

        status_map = {
            statusType.SUCCESS: "successful",
            statusType.INVALID: "invalid",
            statusType.ERROR: "errors"
        }

        for report in reports:
            # Conta por status
            if report.status in status_map:
                stats[status_map[report.status]] += 1

            # Conta por tipo
            is_welcome = report.message_type == messageType.WELCOME

            if is_welcome:
                stats["welcome_reports"] += 1
                if report.status == statusType.SUCCESS:
                    stats["welcome_success"] += 1
            else:
                stats["general_reports"] += 1
                if report.status == statusType.SUCCESS:
                    stats["general_success"] += 1

        # Calcula percentagem de sucesso
        if stats["total"] > 0:
            stats["success_%"] = int(round((stats["successful"] / stats["total"] * 100), 0))

        return stats

    @staticmethod
    def generate_table_html(reports: List[Result]) -> str:
        status_config = {
            statusType.SUCCESS: ("OK", "success"),
            statusType.INVALID: ("INVÁLIDO", "invalid"),
            statusType.ERROR: ("ERRO", "error")
        }

        type_config = {
            messageType.WELCOME: ("Boas-vindas", "type-welcome"),
            messageType.GENERAL: ("Geral", "type-general")
        }

        rows = []
        for report in reports:
            # Obtém configuração de status
            status_text, status_class = status_config.get(
                report.status,
                ("ERRO", "error")
            )

            # Obtém configuração de tipo
            type_text, type_class = type_config.get(
                report.message_type,
                ("Geral", "type-general")
            )

            rows.append(f"""            <tr>
                <td>{report.contact_name}</td>
                <td>{report.contact_phone}</td>
                <td class=\"{type_class}\">{type_text}</td>
                <td class=\"{status_class}\">{status_text}</td>
                <td>{report.message}</td>
                <td>{report.timestamp}</td>
            </tr>""")

        # Retorna tabela completa
        return f"""    <table>
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
{'\n'.join(rows)}
        </tbody>
        </table>"""

    @staticmethod
    def generate_html_report(reports: List[Result], method: str, output_file: Path) -> bool:
        try:
            # Obtém dados
            stats = ReportGenerator.generate_statistics(reports)
            table = ReportGenerator.generate_table_html(reports)
            
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
        .summary {{ margin: 20px 0; }}
        .summary p {{ margin: 8px 0; }}
        .success {{ color: green; }}
        .error {{ color: red; }}
        .invalid {{ color: orange; font-weight: bold; }}
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
        <p><strong>Total de envios:</strong> {stats["total"]}</p>
        <p class="success"><strong>Sucesso:</strong> {stats["successful"]}/{stats["total"]} ({stats["success_pct"]:.1f}%)</p>
        <p class="invalid"><strong>Números Inválidos:</strong> {stats["invalid"]}/{stats["total"]}</p>
        <p class="error"><strong>Erros:</strong> {stats["errors"]}/{stats["total"]}</p>
        <p><strong>Boas-vindas:</strong> {stats["welcome_reports"]} ({stats["welcome_success"]} com sucesso)</p>
        <p><strong>Mensagens gerais:</strong> {stats["general_reports"]} ({stats["general_success"]} com sucesso)</p>
    </div>
    
    <h2>Detalhes</h2>
{table}
    
    <div class="footer">
        <p>Relatório gerado automaticamente</p>
    </div>
</body>
</html>
"""
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return True
            
        except Exception as e:
            get_logger().error(f"Erro ao gerar relatório HTML ", source="ReportService", error=e)
            return False
        
    @staticmethod
    def open_report(report_file: Path) -> bool:
        try:
            if os.name == 'nt':  # Windows
                os.startfile(str(report_file))
            else:  # Linux/Mac
                webbrowser.open(f'file://{report_file}')
            return True
        except Exception as e:
            get_logger().error(f"Não foi possível abrir relatório ", source="ReportService", error=e)
            return False
    
    @staticmethod
    def create_report_filename(method: str, base_dir: Path) -> Path|None:
        try:
            reports_dir = base_dir / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = reports_dir / f"relatorio_{method}_{timestamp}.html"
            
            return report_file
        except Exception as e:
            get_logger().error(f"Erro ao criar nome de ficheiro para relatório ", source="ReportService", error=e)
            return None