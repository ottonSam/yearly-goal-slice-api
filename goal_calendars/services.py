import json
import os

from openai import OpenAI


class DeepSeekWeeklyReportService:
    def __init__(self):
        self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        self.base_url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
        self.model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')

        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY is not configured.")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def generate_week_report(self, week_context):
        system_prompt = (
            "Você é um analista de produtividade e execução de metas. "
            "Use a metodologia de metas anuais quebradas em ciclos de semanas. "
            "Escreva um relatório curto, objetivo e acionável em português, com no máximo 8 linhas. "
            "Considere que 85% de conclusão já representa bom desempenho. "
            "Exemplo de relatório: 'Semana pouco produtiva, com apenas 60% das atividades concluídas, margem inferior as métricas das semanas anteriores. As atividades (Academia, e Corrida) apresentaram uma taxa de conclusão, mas as (Estudo Matemática) ficou muito a baixo do esperado. Recomendo focar em manter consistência e evitar mudanças de prioridade no meio da semana. Tente planejar melhor as atividades para a próxima semana.'"
            )
        user_prompt = (
            "Gere um relatório curto com base nos dados abaixo:\n"
            f"{json.dumps(week_context, ensure_ascii=False, indent=2)}"
        )

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.3,
            max_tokens=450,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = (response.choices[0].message.content or '').strip()
        if not content:
            raise RuntimeError("DeepSeek returned an empty report.")

        return content
