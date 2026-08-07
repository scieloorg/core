import json
from django import forms

class ReadOnlyPrettyJSONWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update({
            'readonly': True,
            'rows': 20,
            'style': (
                'font-family: monospace;'
            ),
        })

    def format_value(self, value):
        if not value:
            return ''
        try:
            parsed = json.loads(value) if isinstance(value, str) else value
            return json.dumps(
                parsed,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
                default=str,   # fallback: converte qualquer coisa para str
            )
        except (json.JSONDecodeError, TypeError):
            return value