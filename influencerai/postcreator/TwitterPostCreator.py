import random
import string
from PIL import Image
from typing import Dict
from emoji.core import emojize
import streamlit as st
import tweepy
import emoji
import os
import config
from postcreator.EmojiDictionary import emojiDict

####################################################
# Globals
####################################################

consumer_key = config.twitter_consumer_key
consumer_secret = config.twitter_consumer_secret
access_token = config.twitter_access_token
access_token_secret = config.twitter_access_token_secret

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

####################################################
# Functions
####################################################


@st.cache(allow_output_mutation=True)
def _get_static_store() -> Dict:
    """This dictionary is initialized once
     and can be used to store the files uploaded"""
    return {}


def _twitter_char_limit(post):
    emojis = list(filter(lambda p: p.startswith(':') & p.endswith(':'), post.split()))
    for e in emojis:
        post = post.replace(e, ' ')
    # print(emojis, len(post))
    return (True, len(post)) if len(post) <= 280 else (False, len(post))


def _preview_tweet(stColumn: st, tweet: string, static_store):
    tweetPostDict = {}
    for i, post in enumerate(tweet.split('\n\n\n')):
        tweetPostDict[i] = {'text': emoji.emojize(post, use_aliases=False)}
        isCharLimit, charLen = _twitter_char_limit(post)
        if isCharLimit:
            stColumn.info(f"Post {str(i+1)} --- Char Length: {str(charLen)}")
        else:
            stColumn.error(f"Post {str(i+1)} --- Char Length: {str(charLen)}")
        for line in post.split('\n'):
            stColumn.markdown(emoji.emojize(line, use_aliases=False), unsafe_allow_html=True)
        selectedImgs = stColumn.multiselect("Select Images", static_store.keys(), key=str(i))
        tweetPostDict[i]['image'] = selectedImgs
        for img in selectedImgs:
            stColumn.image(_load_image(static_store[img]), width=250)
    # print(tweetPostDict)
    return tweetPostDict


def _load_image(image_file):
    return Image.open(image_file, mode='r')


def _save_uploadedfile(uploadedfile):
    tmpUploadDir = os.path.join(os.getcwd(), 'tmpUploads')
    if not os.path.exists(tmpUploadDir):
        os.makedirs(tmpUploadDir)
    with open(os.path.join(tmpUploadDir, uploadedfile.name), "wb") as f:
        f.write(uploadedfile.getbuffer())
        # return st.success("Saved File:{} to Data".format(uploadedfile.name))


def _delete_tmpdirfiles_after_upload():
    # Delete files left in tmpDir after images have been uploaded
    tmpUploadDir = os.path.join(os.getcwd(), 'tmpUploads')

    try:
        for file in os.listdir(tmpUploadDir):
            os.remove(os.path.join(tmpUploadDir, file))
    except OSError as e:
        print(f"Error: {tmpUploadDir} : {e.strerror}")


def _post_to_twitter(tweetPost: dict, static_store):
    # vaiables
    tmpUploadDir = os.path.join(os.getcwd(), 'tmpUploads')

    # post regular tweet
    if len(tweetPost) == 1:
        if len(tweetPost[0]['image']) > 0:
            imgName = tweetPost[0]['image'][0]
            res = api.media_upload(filename=os.path.join(tmpUploadDir, imgName))
            media_ids = [res.media_id]
            api.update_status(status=tweetPost[0]['text'], media_ids=media_ids)

        else:
            # post only tweet
            api.update_status(status=tweetPost[0]['text'])

    elif len(tweetPost) > 1:
        twitterId = None
        for tweet in tweetPost.values():
            # post media tweet
            if len(tweet['image']) > 0:

                # Upload images and get media_ids
                media_ids = []
                for imgName in tweet['image']:
                    res = api.media_upload(filename=os.path.join(tmpUploadDir, imgName))
                    media_ids.append(res.media_id)
                    print("Added one")

                # post subpost with image
                if twitterId is None:
                    twitterId = api.update_status(status=tweet['text'], media_ids=media_ids)
                    print("Tweet + Image")

                else:
                    # post with link to previous tweet
                    twitterId = api.update_status(status=tweet['text'], media_ids=media_ids, in_reply_to_status_id=twitterId, auto_populate_reply_metadata=True)
                    print("Tweet + Image Sub")

            elif twitterId:
                # post with link to previous tweet
                twitterId = api.update_status(status=tweet['text'], in_reply_to_status_id=twitterId, auto_populate_reply_metadata=True)
                print("Tweet Sub")
            else:
                twitterId = api.update_status(status=tweet['text'])
                print("Tweet")

            twitterId = twitterId.id
    _delete_tmpdirfiles_after_upload()


def schedule_tweet(schedDate, schedTime, tweet):
    tweetdf = 'c:\\Users\\kornas\\Desktop\\SocialAI\\InfluencerAI\\influencerai\\tools\\TweetScheduler\\tweetsdf.pickle'
    with open(tweetdf, "rb") as tweets:
        df = pickle.load(tweets)

    data = {
        'sno': len(df) + 1,
        'tweet': tweet,
        'tweet_at': f'{str(schedDate)} {str(schedTime)}',
        'sent': False,
    }


    df = df.append(data, ignore_index=True)

    with open(tweetdf, "wb") as tweets:
        df = pickle.dump(df, tweets)
    st.success('Tweet has been scheduled')


####################################################
# Main function
####################################################


def twitter_postcreator_view():

    # Variables
    twitterPost = []
    static_store = _get_static_store()

    #####################################################################
    # Create sidebar
    st.sidebar.write("Sidbar this is",)
    if search_emoji := st.sidebar.text_input("Search Emojis"):
        foundEmojis = list(filter(lambda x: x.find(search_emoji.lower()) != -1, emojiDict))
        foundEmojized = [lambda x: emojize(x) for x in  foundEmojis]
        st.sidebar.markdown(emojize(' '.join(foundEmojis)))

    #####################################################################
    # Create Title and Subtitle
    rightTitleCol, leftSuccessPostStat = st.columns(2)
    rightTitleCol.header("Twitter")

    subheaderLeftCol, newPostRightCol, postToTwitterRightCol, col4, col5, col6 = st.columns([2,1,1,1,1,1])
    subheaderLeftCol.subheader('Twitter Post Creator')
    postBtn = postToTwitterRightCol.button('🐦Post to Twitter')
    newPost = newPostRightCol.button('🔄 Create New Post')

    schedBtn = col4.button('📘 Schedule Post')
    schedDate = col5.date_input('Schedule Date',)
    schedTime = col6.time_input('Schedule Time')

    #####################################################################
    # Create right column for writing post and left column for previewing post
    writePostTextAreaRightColumn, previewPostTextAreaLeftColumn = st.columns(2)
    tweet = writePostTextAreaRightColumn.text_area("Post", height=250)
    previewPostTextAreaLeftColumn.text("Preview")
    tweetPost = _preview_tweet(previewPostTextAreaLeftColumn, tweet, static_store)

    #####################################################################
    # Bottom section for uploading and previewing images
    st.subheader("Upload Images")

    con1 = st.container()
    narrowRightCol, wideLeftCol = con1.columns([1, 5])

    # Create photos uploader
    uploadedFiles = wideLeftCol.file_uploader("Upload", accept_multiple_files=True)

    # Extra spaces to center below buttons
    narrowRightCol.write(" ")
    narrowRightCol.write(" ")

    # Create buttons for clearing and showing uploaded photos
    clearUploadsBtn = narrowRightCol.button("Clear file list")
    showUploadsBtn = narrowRightCol.checkbox("Show content of files?")

    # Center column for diplaying the uploaded photos
    _, photoCenter, _ = st.columns(3)

    if uploadedFiles:
        for file in uploadedFiles:
            # Process you file here
            value = file.getvalue()

            # And add it to the static_store if not already in
            if file.name not in static_store.values():
                static_store[file.name] = file
                _save_uploadedfile(file)

    if clearUploadsBtn:
        static_store.clear()
        _delete_tmpdirfiles_after_upload()

    if showUploadsBtn:
        for img in static_store.values():
            photoCenter.image(_load_image(img), width=450)
            # print(static_store.keys())

    if postBtn:
        try:
            _post_to_twitter(tweetPost, static_store)
            leftSuccessPostStat.success("Tweet has been posted")
        except Exception as e:
            leftSuccessPostStat.error(f"Post Unsuccessful: {str(e)}")

    if newPost:
        del tweet
        del tweetPost
        static_store.clear()
        _delete_tmpdirfiles_after_upload()
