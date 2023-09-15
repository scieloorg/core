from django.db import models
from django.http import JsonResponse
from django.template.response import TemplateResponse
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtailcaptcha.models import WagtailCaptchaEmailForm


class HomePage(Page):
    pass

class FormField(AbstractFormField):
    page = ParentalKey("FormPage", on_delete=models.CASCADE, related_name="form_fields")


class FormPage(WagtailCaptchaEmailForm):
    intro = RichTextField(blank=True, help_text="Texto de introdução ao formulário.")
    thank_you_text = RichTextField(
        blank=True,
        help_text="Adicione a mensagem que será exibido após o envio do formulário.",
    )

    def serve(self, request, *args, **kwargs):
        if request.method == "POST":
            form = self.get_form(
                request.POST, request.FILES, page=self, user=request.user
            )

            if request.is_ajax():
                if form.is_valid():
                    self.process_form_submission(form)
                    return JsonResponse(
                        {
                            "alert": "success",
                            "message": self.thank_you_text
                            if self.thank_you_text
                            else "Formulário enviado com sucesso!",
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "alert": "error",
                            "message": "Erro ao tentar enviar a <strong>formulário!</strong> Verifique os campos obrigatórios. Errors: %s"
                            % form.errors,
                        }
                    )
            else:
                if form.is_valid():
                    form_submission = self.process_form_submission(form)
                    return self.render_landing_page(
                        request, form_submission, *args, **kwargs
                    )
        else:
            form = self.get_form(page=self, user=request.user)

        context = self.get_context(request)
        context["form"] = form
        return TemplateResponse(request, self.get_template(request), context)

    class Meta:
        verbose_name = "Página com formulário."
        verbose_name_plural = "Páginas com formulários."

    content_panels = WagtailCaptchaEmailForm.content_panels + [
        FormSubmissionsPanel(),
        FieldPanel("intro", classname="full"),
        InlinePanel("form_fields", label="Form fields"),
        FieldPanel("thank_you_text", classname="full"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("from_address", classname="col6"),
                        FieldPanel("to_address", classname="col6"),
                    ]
                ),
                FieldPanel("subject"),
            ],
            "Email",
        ),
    ]
