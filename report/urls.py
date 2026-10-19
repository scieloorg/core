from django.urls import path

from report.views import (
    data_availability_options_view,
    data_availability_view,
    report_index_view,
)

urlpatterns = [
    path("", report_index_view, name="report_index"),
    path(
        "data-availability/",
        data_availability_view,
        name="report_data_availability",
    ),
    path(
        "data-availability/options/",
        data_availability_options_view,
        name="report_data_availability_options",
    ),
]
