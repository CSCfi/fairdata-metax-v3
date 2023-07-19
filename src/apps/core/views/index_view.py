from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView


class IndexView(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    template_name = "core/index.html"

    def get(self, request):
        return Response()
