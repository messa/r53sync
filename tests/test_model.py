
from r53sync import model


def test_hosted_zone_from_aws():
    data = {
        'CallerReference': '80AAAAAA-C53C-E79E-8D15-C44B05AAAAAA',
        'Id': '/hostedzone/Z1AAAA51AAAAAA',
        'Config': {'PrivateZone': False},
        'Name': 'example.com.',
        'ResourceRecordSetCount': 4
    }
    hz = model.hosted_zone_from_aws(data)
    assert hz.id == '/hostedzone/Z1AAAA51AAAAAA'
    assert hz.name == 'example.com.'
    assert hz.rrs_count == 4
    assert hz.comment == None
