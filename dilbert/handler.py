import json
import random
import re
import urllib

import boto3

from datetime import datetime, timedelta


_comic_url_re = re.compile('\s+src="(?P<url>http://assets.amuniversal.com/[a-f0-9]+)"(\s\/)?>')
_days_ago_re = re.compile('(?P<days>\w+) days ago')
_int_days_ago_re = re.compile('(?P<days>\d{1,2}) days ago')
_last_int_days = re.compile('last (?P<days>[12345])')
_comic_url_re = re.compile('\s+src="(?P<url>http://assets.amuniversal.com/[a-f0-9]+)"(\s\/)?>')
_tag_re = re.compile('href\=\"\/search_results\?terms=(?P<tag>\w+)\"\>')

AWS_REGION = 'us-west-2'
TABLE_NAME = 'devDilbert'
DEFAULT_DATE_FMT = '%Y-%m-%d'
MAX_COMICS = 5

# global dynamodb table
_table = None


def text_to_int(textnum):
    units = [
        'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight',
        'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
        'sixteen', 'seventeen', 'eighteen', 'nineteen',
    ]
    tens = ['', '', 'twenty', 'thirty']
    numwords = {'and': (1, 0)}

    for idx, word in enumerate(units):
        numwords[word] = (1, idx)
    for idx, word in enumerate(tens):
        numwords[word] = (1, idx * 10)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
            return

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current


def get_comic_url(dt):
    return 'http://dilbert.com/strip/%s' % (dt.strftime(DEFAULT_DATE_FMT), )


def _get_dt_from_days_ago(message):
    """Use a couple of regexes to get number of days from a textual message

    Returns a datetime for `days_ago` or `now` if no days ago message can be found.

    """
    if not message:
        return

    days_ago = _int_days_ago_re.search(message)
    if days_ago:
        days = days_ago.group('days')
    else:
        days_ago = _days_ago_re.search(message)
        if days_ago:
            days = days_ago.group('days')
            days = text_to_int(days)

    if not days_ago:
        return

    return _get_dt_from_days(days)


def _get_dt_from_days(days):
    try:
        now = datetime.now()
        days = int(days)
        return now - timedelta(days=days)
    except ValueError:
        pass


def _get_dt_from_date(message):
    """Returns a datetime object if the message matches any supported format.

    Returns None if no date can be parsed.

    """
    if not message:
        return

    formats = (
        DEFAULT_DATE_FMT,
        '%m-%d-%y',
        '%m.%d.%y',
        '-%m-%-d-%y',
        '-%m.%-d.%y',
        '%Y/-%-m/-%-d',
        '%b %-d',
        '%b, %-d',
    )
    for f in formats:
        try:
            return datetime.strptime(message, f)
        except ValueError:
            pass


def get_datetime_from_message(message):
    """Returns a datetime object from a textual message for any of our supported formats."""
    now = datetime.now()
    if message == 'yesterday':
        return now - timedelta(days=1)

    dt = _get_dt_from_days_ago(message)
    if dt:
        return dt

    dt = _get_dt_from_date(message)
    if dt:
        return dt

    return datetime.now()


def get_random_datetime():
    days = random.randint(1, 366)
    return datetime.now() - timedelta(days=days)


def _init_db():
    global _table
    if not _table:
        _db = boto3.resource('dynamodb', region_name=AWS_REGION)
        _table = _db.Table(TABLE_NAME)

def get_image_url_from_db(dt):
    _init_db()
    post_day = dt.strftime(DEFAULT_DATE_FMT)
    data = _table.get_item(Key={'postDay': post_day})
    record = data.get('Item', {})
    print 'Returned from dynamo', record
    return record.get('url')


def save_tags(url, tags):
    for tag in tags:
        data = _table.get_item(Key={'postDay': tag})
        record = data.get('Item')
        if not record:
            item = {'postDay': tag, 'urls': [url]}
        else:
            urls = set(record['urls'])
            urls.add(url)
            item = {'postDay': tag, 'urls': list(urls)}
        _table.put_item(Item=item)


def save_image_url_to_db(image_url, dt, tags):
    print 'Saving to dynamo'
    _init_db()
    post_day = dt.strftime(DEFAULT_DATE_FMT)
    item = {
        'postDay': post_day,
        'url': image_url,
        'tags': tags,
    }
    _table.put_item(Item=item)


def get_image_url(url, dt):
    image_url = get_image_url_from_db(dt)
    if image_url:
        return image_url

    print 'fetching url', url
    u = urllib.urlopen(url)
    html = u.read()

    found = _comic_url_re.search(html)
    if found:
        image_url = found.group('url')
        tags = _tag_re.findall(html)
        save_image_url_to_db(image_url, dt, tags)
        save_tags(url, tags)

    return image_url


def get_slack_json(url, dt):
    return {
        'response_type': 'in_channel',
        'text': 'Dilbert for %s:' % (dt.strftime('%Y-%m-%d'), ),
        'attachments': [
            {
                'title': 'Dilbert',
                'title_link': url,
                'text': url,
                'image_url': get_image_url(url, dt),
            }
        ]
    }


def get_multiple(n):
    # sanity check..b/c people are evil. Also, the regex to match the command/post should catch
    # this but leave it in as a safety check
    if n > MAX_COMICS:
        n = MAX_COMICS
    if n < 1:
        n = 1

    # get the last n days, inclusive of today
    dts = [_get_dt_from_days(d) for d in xrange(n + 1)]
    urls = [(dt, get_comic_url(dt)) for dt in dts]
    attachments = [{
                'text': 'Dilbert for %s:' % (dt.strftime('%Y-%m-%d'), ),
                'title_link': url,
                'text': url,
                'image_url': get_image_url(url, dt),
        } for (dt, url) in urls]
    attachments.reverse()
    return {
        'response_type': 'in_channel',
        'text': 'Dilberts for last %d days:' % (n, ),
        'attachments': attachments,
    }


def dilbert(event, context):
    """Build the URL for a Dilbert comic with the following language/spec:

        /dilbert -> Reply with today's comic
        /dilbert random -> Reply with a random comic from the past year
        /dilbert yesterday -> Reply with yesterday's comic
        /dilbert $N days ago -> Reply with a comic from $N days ago where $N can be an
                                integer or written number (ie, "2" or "two")
        /dilbert $DATE -> Reply with a comic from a specific date with multiple formats
        /dilbert last [1-5] -> Reply with the last n comics, inclusive of today

    """
    print event
    query_params = event.get('queryStringParameters') or {}

    # uncomment this line to add authentication so that only your slash command can call this
    # endpoint
    # assert query_params['token'] == 'your-slash-command-token'

    date = query_params.get('text', '').strip().lower()

    # see if we're looking up multiple days
    get_last_n_days = _last_int_days.search(date)
    if get_last_n_days:
        n = int(get_last_n_days.group('days'))
        slash_json =  get_multiple(n)
    else:
        dt = get_random_datetime() \
                if date == 'random' \
                else get_datetime_from_message(date)
        url = get_comic_url(dt)
        slash_json = get_slack_json(url, dt)

    response = {
        'statusCode': 200,
        'body': json.dumps(slash_json)
    }

    return response

if __name__ == '__main__':
    fn = '../2017-02-13.html'
    with open(fn, 'r') as fh:
        html = fh.read()

    found = _comic_url_re.search(html)
    if found:
        image_url = found.group('url')
        print image_url
        print _tag_re.findall(html)
