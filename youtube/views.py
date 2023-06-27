from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Channel, ChannelDetail
from community.serializers import BoardSerializer, BoardCreateSerializer
from . import serializers
from . import youtube_api
from django.db import transaction

class FindChannel(APIView):
    """
    채널 조회

    검색결과 중 상위 5개를 딕셔너리를 포함한 리스트로 출력

    data = [{
        "channel_name",
        "channel_id",
        "subscriber",
        "thumbnail"
    },...]
    """

    def post(self, request, channel):
        youtube = youtube_api.youtube
        channels = youtube_api.find_channelid(youtube, channel)
        return Response(channels, status=status.HTTP_200_OK)


class ChannelModelView(APIView):
    def get(self, request, channel_id):
        channel = get_object_or_404(Channel,channel_id=channel_id)
        serializer = serializers.ChannelSerializer(channel)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    def post(self, request, channel_id):
        youtube = youtube_api.youtube
        channel = Channel.objects.filter(channel_id=channel_id).exists()
        if channel:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            channel_data = youtube_api.get_channel_stat(youtube, channel_id)
            with transaction.atomic():
                serializer = serializers.CreateChannelSerializer(data=channel_data)
                if serializer.is_valid():
                    channel = serializer.save()
                    try:
                        channel_detail_data = youtube_api.get_latest30_video_details(youtube, channel_data)
                    except:
                        return Response(status=status.HTTP_400_BAD_REQUEST)
                    channel_data.update(channel_detail_data)
                    detail_serializer = serializers.CreateChannelDetailSerializer(
                        data=channel_data
                    )
                    if detail_serializer.is_valid():
                        detail_serializer.save(channel=channel)
                    else:
                        return Response(
                            {"channel_detail_error": detail_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    board_serializer = BoardCreateSerializer(data=channel_data)
                    if board_serializer.is_valid():
                        board_serializer.save(channel=channel)
                        return Response(status=status.HTTP_201_CREATED)
                    else:
                        return Response(
                            {"board_error": board_serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    return Response(
                        {"channel_error": serializer.errors},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, channel_id):
        channel = get_object_or_404(Channel,channel_id=channel_id)
        youtube = youtube_api.youtube
        try:
            channel_data = youtube_api.get_channel_stat(youtube, channel_id)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.ChannelSerializer(
            instance=channel, data=channel_data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, channel_id):
        channel = get_object_or_404(Channel, channel_id=channel_id)
        channel.delete()
        return Response(status=status.HTTP_200_OK)


class ChannelDetailView(APIView):
    def get(self, request, custom_url):
        channel = get_object_or_404(Channel, custom_url=custom_url)
        detail = ChannelDetail.objects.filter(channel=channel.pk).order_by('-updated_at').first()
        serializer = serializers.ChannelDetailSerializer(detail)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, custom_url):
        youtube = youtube_api.youtube
        channel = get_object_or_404(Channel, custom_url=custom_url)
        try:
            channel_data = youtube_api.get_channel_stat(youtube, channel.channel_id)
            with transaction.atomic():
                try:
                    channel_data = youtube_api.get_channel_stat(youtube, channel.channel_id)
                    channel_detail_data = youtube_api.get_latest30_video_details(youtube, channel_data)
                except:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                channel_data.update(channel_detail_data)
                detail_serializer = serializers.CreateChannelDetailSerializer(
                    data=channel_data
                )
                if detail_serializer.is_valid():
                    detail_serializer.save(channel=channel)
                else:
                    return Response(
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)