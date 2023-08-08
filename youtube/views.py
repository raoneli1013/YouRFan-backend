from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from community.serializers import BoardCreateSerializer
from youtube.models import Channel, ChannelDetail
from youtube import serializers
from youtube import youtube_api
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from .throttling import ObjectThrottle
import datetime
import logging



class FindChannel(APIView):
    """채널 검색
    검색결과 중 상위 5개를 딕셔너리를 포함한 리스트로 출력
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ObjectThrottle]

    def post(self, request, channel):
        try:
            channels = youtube_api.find_channelid(channel)
        except:
            Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(channels, status=status.HTTP_200_OK)


class ChannelAPIView(APIView):
    """채널 조회 및 생성
    Youtube 고유 채널 ID 필요, 거의 변하지 않는 값들이 저장됩니다.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ObjectThrottle]
    def get(self, request, channel_id):
        try:
            channel = Channel.objects.get(channel_id=channel_id)
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        serializer = serializers.ChannelSerializer(channel)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, channel_id):
        channel = Channel.objects.filter(channel_id=channel_id).exists()
        if channel:
            return Response(status=status.HTTP_406_NOT_ACCEPTABLE)
        try:
            channel_data = youtube_api.get_channel_stat(channel_id)
            if not "upload_list" in channel_data:
                return Response(status=status.HTTP_410_GONE)
            if int(channel_data["subscriber"]) < 10000:
                return Response(status=status.HTTP_423_LOCKED)
            with transaction.atomic():
                serializer = serializers.CreateChannelSerializer(data=channel_data)
                if serializer.is_valid():
                    channel = serializer.save()
                    channel_detail_data = youtube_api.get_latest30_video_details(
                        channel_data
                    )
                    channel_data.update(channel_detail_data)
                    channel_heatmap_url = youtube_api.create_channel_heatmap_url(
                        channel_data
                    )
                    channel_data["channel_activity"] = channel_heatmap_url
                    wordcloud_url = youtube_api.create_wordcloud_url(channel_data)
                    channel_data["channel_wordcloud"] = wordcloud_url
                    detail_serializer = serializers.CreateChannelDetailSerializer(
                        data=channel_data
                    )
                    if detail_serializer.is_valid():
                        detail_serializer.save(channel=channel)
                    else:
                        raise Exception(detail_serializer.errors)
                    board_serializer = BoardCreateSerializer(data=channel_data)
                    if board_serializer.is_valid():
                        board_serializer.save(channel=channel)
                        return Response(status=status.HTTP_201_CREATED)
                    else:
                        raise Exception(board_serializer.errors)
                else:
                    raise Exception(serializer.errors)
        except Exception as e:
            return Response(e,status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, channel_id):
        channel = get_object_or_404(Channel, channel_id=channel_id)
        youtube = youtube_api.youtube
        try:
            channel_data = youtube_api.get_channel_stat(channel_id)
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


class ChannelDetailAPIView(APIView):
    """채널 상세 정보 조회 및 생성
    """
    def get(self, request, custom_url):
        channel = get_object_or_404(Channel, custom_url=custom_url)
        detail = (
            ChannelDetail.objects.filter(channel=channel.pk)
            .order_by("-updated_at")
            .first()
        )
        serializer = serializers.ChannelDetailSerializer(detail)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, custom_url):
        youtube = youtube_api.youtube
        channel = get_object_or_404(Channel, custom_url=custom_url)
        try:
            with transaction.atomic():
                try:
                    channel_data = youtube_api.get_channel_stat(
                        youtube, channel.channel_id
                    )
                    channel_detail_data = youtube_api.get_latest30_video_details(
                        youtube, channel_data
                    )
                except:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
                channel_data.update(channel_detail_data)
                channel_heatmap_url = youtube_api.create_channel_heatmap_url(
                    channel_data
                )
                channel_data["channel_activity"] = channel_heatmap_url
                wordcloud_url = youtube_api.create_wordcloud_url(channel_data)
                channel_data["channel_wordcloud"] = wordcloud_url
                detail_serializer = serializers.CreateChannelDetailSerializer(
                    data=channel_data
                )
                if detail_serializer.is_valid():
                    detail_serializer.save(channel=channel)
                    return Response(status=status.HTTP_200_OK)
                else:
                    return Response(
                        detail_serializer.errors,
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except:
            return Response(status=status.HTTP_400_BAD_REQUEST)

def updata_detail_data():
    logging.basicConfig(filename='update_error.log', level=logging.ERROR)
    youtube = youtube_api.youtube
    channels = Channel.objects.all()
    for channel in channels:
        try:
            with transaction.atomic():
                try:
                    channel_data = youtube_api.get_channel_stat(
                        youtube, channel.channel_id
                    )
                    channel_detail_data = youtube_api.get_latest30_video_details(
                        youtube, channel_data
                    )
                except:
                    raise Exception("data를 불러오지 못했습니다")
                channel_data.update(channel_detail_data)
                channel_heatmap_url = youtube_api.create_channel_heatmap_url(
                    channel_data
                )
                channel_data["channel_activity"] = channel_heatmap_url
                wordcloud_url = youtube_api.create_wordcloud_url(channel_data)
                channel_data["channel_wordcloud"] = wordcloud_url
                detail_serializer = serializers.CreateChannelDetailSerializer(
                    data=channel_data
                )
                if detail_serializer.is_valid():
                    detail_serializer.save(channel=channel)
                else: 
                    raise Exception(detail_serializer.errors)
        except Exception as e:
            logging.exception(channel.title, channel.channel_id, e)

