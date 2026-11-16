from django.db.models import QuerySet
from django.utils.functional import cached_property, classproperty

from wagtail.admin.admin_url_finder import AdminURLFinder
from wagtail.admin.views.bulk_action import BulkAction
from wagtail.permissions import policy_registry
from wagtail.snippets.models import get_snippet_models


class SnippetBulkAction(BulkAction):
    @classproperty
    def models(cls):
        # We used to set `models = get_snippet_models()` directly on the class,
        # but this is problematic because it means that the list of models is
        # evaluated at import time.

        # Bulk actions are normally registered in wagtail_hooks.py, but snippets
        # can also be registered in wagtail_hooks.py. Evaluating
        # get_snippet_models() at import time could result in either a circular
        # import or an incomplete list of models.
        return get_snippet_models()

    @cached_property
    def permission_policy(self):
        return policy_registry.get_by_type(self.model)

    def get_all_objects_in_listing_query(self, parent_id):
        # The listing's query parameters are passed along with `id=all`, so let
        # the listing view itself work out which objects it was showing. This
        # keeps the search, filters and locale in sync with the listing without
        # duplicating its logic here.
        view_function = self.model.snippet_viewset.index_view
        view = view_function.view_class(**view_function.view_initkwargs)
        view.setup(self.request)
        results = view.get_queryset()
        if isinstance(results, QuerySet):
            return results.order_by().values_list("pk", flat=True)
        # A search backend returns search results rather than a queryset
        return [obj.pk for obj in results]

    def object_context(self, snippet):
        return {
            "item": snippet,
            "edit_url": AdminURLFinder(self.request.user).get_edit_url(snippet),
        }

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "header_icon": self.model.snippet_viewset.icon,
            }
        )
        return super().get_context_data(**kwargs)

    def get_execution_context(self):
        return {**super().get_execution_context(), "self": self}
