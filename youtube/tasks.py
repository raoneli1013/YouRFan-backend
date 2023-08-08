from celery import shared_task


# 채널 댓글 가져오기
@shared_task
def get_channel_comment(youtube, channel_id, day_delta=0):
    comments = []
    next_page_token = None
    more_pages = True
    count = 1
    today = datetime.now(timezone.utc)
    while more_pages:
        request = youtube.commentThreads().list(
            part="snippet",
            allThreadsRelatedToChannelId=channel_id,
            maxResults=100,
            pageToken=next_page_token,
        )
        response = request.execute()

        comments += response["items"]
        published_at = datetime.strptime(comments[-1]['snippet']['topLevelComment']['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)
        if (today-published_at).days>=day_delta: break
        next_page_token = response.get("nextPageToken")
        count += 1
        if next_page_token is None or count > 30:
            more_pages = False
    weekly_data = {'Monday':[],'Tuesday':[],'Wednesday':[],'Thursday':[],'Friday':[],'Saturday':[],'Sunday':[]}
    for data in comments:
        published_at = datetime.strptime(data['snippet']['topLevelComment']['snippet']['publishedAt'], "%Y-%m-%dT%H:%M:%S%z") + timedelta(hours=9)
        if (today-published_at).days>=day_delta: break
        weekly_data[published_at.strftime("%A")].append(published_at.strftime("%H"))
    
    return comments