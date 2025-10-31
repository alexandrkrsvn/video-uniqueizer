from rest_framework import serializers

class JobSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    progress_overall = serializers.IntegerField()
    total_tasks = serializers.IntegerField()
    done_tasks = serializers.IntegerField()
    input_folder = serializers.CharField()
    output_folder = serializers.CharField()
    message = serializers.CharField(allow_blank=True)
    created_at = serializers.CharField()
