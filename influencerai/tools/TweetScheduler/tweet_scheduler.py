import os
import logging
import arrow
import tweepy
import config
import pickle
import pandas as pd
from apscheduler.schedulers.background import BlockingScheduler

logging.basicConfig(filename='./SchedulerLog.txt', level=logging.INFO)
logger = logging.getLogger(__name__)


def send_tweets(consumer_key, consumer_secret, access_token,
                access_token_secret, tweetPost):
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(auth)

    logging.info('sending tweet')

    # api.update_status(tweet)
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
    #_delete_tmpdirfiles_after_upload()

    logging.info('tweet sent')


def switch_to_arrow(df):
    df['tweet_at'] = arrow.get(df['tweet_at'])
    return df


def get_non_sent_tweets(consumer_key, consumer_secret, access_token, access_token_secret):
    tweetdf = 'c:\\Users\\kornas\\Desktop\\SocialAI\\InfluencerAI\\influencerai\\tools\\TweetScheduler\\tweetsdf.pickle'
    with open(tweetdf, "rb") as tweetsPickle:
        df = pickle.load(tweetsPickle)

        new_df = df.apply(switch_to_arrow, axis=1)
        applicable_rows = new_df[(new_df['sent']==False) & (new_df['tweet_at'] < arrow.utcnow())]
        if len(applicable_rows) == 0:
            return
        for index, data in applicable_rows.iterrows():
            send_tweets(
                consumer_key, consumer_secret, access_token, access_token_secret, data['tweet'])
            new_df.loc[new_df['sno'] == data['sno'], 'sent'] = True
    with open(tweetdf, "wb") as tweetsPickle:
        pickle.dump(new_df, tweetsPickle)
        


def tweet_scheduler():
    consumer_key = config.twitter_consumer_key
    consumer_secret = config.twitter_consumer_secret
    access_token = config.twitter_access_token
    access_token_secret = config.twitter_access_token_secret
    get_non_sent_tweets(consumer_key, consumer_secret, access_token, access_token_secret)


if __name__ == '__main__':
    scheduler = BlockingScheduler(timezone="Europe/Warsaw")
    scheduler.add_job(
        tweet_scheduler, 'interval', minutes=10)
    logger.info('starting scheduler')
    scheduler.start()