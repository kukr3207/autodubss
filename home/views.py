from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import UserBNFuturesRelationForm, UserBNOptionsRelationForm
from .models import (
    UserBNFuturesRelation,
    UserBNOptionsRelation,
    UserFyersAppRelation,
)


def _dashboard_context():
    return {
        "bn_futures_form": UserBNFuturesRelationForm(),
        "bn_options_form": UserBNOptionsRelationForm(),
    }


def _fyers_session(app):
    # Import the optional broker SDK only when the OAuth flow is used. This
    # keeps management commands and the local dashboard independent of it.
    from fyers_api import accessToken

    return accessToken.SessionModel(
        client_id=app.fyers_app_id,
        secret_key=app.fyers_app_secretkey,
        redirect_uri=settings.FYERS_REDIRECT_URL,
        response_type="code",
        grant_type="authorization_code",
    )


def _configured_fyers_app(user):
    try:
        app = UserFyersAppRelation.objects.get(user=user)
    except UserFyersAppRelation.DoesNotExist:
        return None
    if not app.fyers_app_id or not app.fyers_app_secretkey:
        return None
    return app


@login_required
@require_GET
def home(request):
    return render(request, "home.html", _dashboard_context())


@login_required
@require_GET
def fyers_authentication(request):
    app = _configured_fyers_app(request.user)
    if app is None:
        messages.error(request, "Add your Fyers application credentials first.")
        return redirect("home")

    try:
        authorization_url = _fyers_session(app).generate_authcode()
    except Exception:
        messages.error(request, "Fyers authentication is temporarily unavailable.")
        return redirect("home")

    return redirect(authorization_url)


@login_required
@require_GET
def fyers_authentication_callback(request):
    auth_code = request.GET.get("auth_code", "").strip()
    app = _configured_fyers_app(request.user)
    if not auth_code or app is None:
        messages.error(request, "Fyers authentication could not be completed.")
        return redirect("home")

    try:
        session = _fyers_session(app)
        session.set_token(auth_code)
        response = session.generate_token()
        access_token = response.get("access_token") if isinstance(response, dict) else None
        if not isinstance(access_token, str) or not access_token.strip():
            raise ValueError("Fyers did not return an access token")
    except Exception:
        messages.error(request, "Fyers authentication could not be completed.")
        return redirect("home")

    request.session["fyers_access_token"] = access_token.strip()
    messages.success(request, "Fyers authentication completed.")
    return redirect("home")


def _save_bot_configuration(request, form_class, model_class, label):
    access_token = request.session.get("fyers_access_token")
    if not access_token:
        messages.error(request, "Authenticate with Fyers before saving a bot.")
        return redirect("home")

    form = form_class(request.POST)
    if not form.is_valid():
        messages.error(request, "Enter a positive number of lots.")
        return redirect("home")

    values = {
        "number_of_lots": form.cleaned_data["number_of_lots"],
        "fyers_access_token": access_token,
    }
    existing = model_class.objects.filter(user_id=request.user).order_by("-date_added")
    configuration = existing.first()
    if configuration is None:
        model_class.objects.create(user_id=request.user, **values)
    else:
        existing.exclude(pk=configuration.pk).delete()
        for field, value in values.items():
            setattr(configuration, field, value)
        configuration.save(update_fields=["number_of_lots", "fyers_access_token"])

    messages.success(request, f"{label} configuration saved.")
    return redirect("home")


@login_required
@require_POST
def bn_futures_form(request):
    return _save_bot_configuration(
        request,
        UserBNFuturesRelationForm,
        UserBNFuturesRelation,
        "Bank Nifty futures bot",
    )


@login_required
@require_POST
def bn_options_form(request):
    return _save_bot_configuration(
        request,
        UserBNOptionsRelationForm,
        UserBNOptionsRelation,
        "Bank Nifty options bot",
    )
