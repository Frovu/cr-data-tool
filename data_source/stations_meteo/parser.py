from datetime import datetime, timezone

AWS_RMP_PAGE = 1024
AWS_RMP_IDX = {
    'Moscow': '91001'
}

def parse_aws_rmp(index, dt_from, dt_to):
    return []

def obtain_aws_rmp(station, time_range, query):
    index = AWS_RMP_IDX[station]
    epoch_range = [t.replace(tzinfo=timezone.utc).timestamp() for t in time_range]
    for dt_from in range(epoch_range[0], epoch_range[1], AWS_RMP_PAGE):
        dt_to = dt_from + AWS_RMP_PAGE
        if dt_to > epoch_range[1]:
            dt_to = epoch_range[1]
        parse_aws_rmp(index, dt_from, dt_to)

def query(station, time_range, query):
    if station == 'Moscow':
        return obtain_aws_rmp(station, time_range, query)
    else:
        return None
