from rest_framework import serializers

class ProcessRequestSerializer(serializers.Serializer):
    process_name= serializers.CharField(max_length=100)
    location= serializers.CharField()