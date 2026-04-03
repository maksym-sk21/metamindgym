from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def site_admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/accounts/login/?next={request.path}')
        if not request.user.is_site_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper