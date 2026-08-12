from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.views.decorators.http import require_POST


def _run_futures_order():
    # The market-data SDKs are optional for normal dashboard use and are only
    # imported for an explicitly requested execution.
    from .logic.run import executeBNFuturesOrder

    return executeBNFuturesOrder()


@staff_member_required
@require_POST
def execute_bn_futures_bot(request):
    try:
        _run_futures_order()
    except Exception:
        messages.error(request, "The futures bot could not be executed.")
    else:
        messages.success(request, "The futures bot completed.")
    return redirect("home")
