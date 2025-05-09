# -*- coding: utf-8 -*-

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import UserActivateKey


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(max_length=30)

    class Meta:
        model = User
        fields = ("username",)

    def clean_email(self):
        email = self.cleaned_data["email"]
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_("A user with that email already exists."))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_active = False
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

    def set_active_key(self):
        return UserActivateKey.set_random_key_for_user(user=self.instance)

    def send_confirm_mail(
        self, request, active_key, template_name="registration/confirm_email.html"
    ):
        from django.contrib.sites.models import Site
        from django.urls import reverse

        from tcms.core.mailto import mailto
        from tcms.core.utils import request_host_link

        s = Site.objects.get_current()
        cu = "{}{}".format(
            request_host_link(request, s.domain),
            reverse("nitrate-activation-confirm", args=[active_key.activation_key]),
        )
        mailto(
            template_name=template_name,
            recipients=self.cleaned_data["email"],
            subject="Your new %s account confirmation" % s.domain,
            context={
                "user": self.instance,
                "site": s,
                "active_key": active_key,
                "confirm_url": cu,
            },
        )
