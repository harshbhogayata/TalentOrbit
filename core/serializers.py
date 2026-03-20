from rest_framework import serializers


class SearchSuggestionQuerySerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True, max_length=100)


class SearchSuggestionItemSerializer(serializers.Serializer):
    pk = serializers.IntegerField(source='id')
    title = serializers.CharField()
    company__company_name = serializers.CharField(source='company_name')
    location = serializers.CharField(allow_blank=True, allow_null=True)


class NewsletterSubscribeSerializer(serializers.Serializer):
    email = serializers.EmailField()
