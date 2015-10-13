
from r53sync.route53 import Route53Client


def test_list_zones():
    class TestBotoClient:

        def list_hosted_zones(self):
            return {
                'HostedZones': [{'CallerReference': '804BAAAA-C53C-E79E-8D15-C44B05AAAAAA',
                                  'Config': {'PrivateZone': False},
                                  'Id': '/hostedzone/AAAA2A51Y0AAAA',
                                  'Name': 'example.com.',
                                  'ResourceRecordSetCount': 4},
                                 {'CallerReference': 'E07AAAAA-42D3-3922-87BC-60ACC8E2AAAA',
                                  'Config': {'Comment': 'Lorem ipsum',
                                             'PrivateZone': False},
                                  'Id': '/hostedzone/AAAAX6KE0IAAAA',
                                  'Name': 'example.net.',
                                  'ResourceRecordSetCount': 7}],
                 'IsTruncated': False,
                 'MaxItems': '100',
                 'ResponseMetadata': {'HTTPStatusCode': 200,
                                      'RequestId': '2b7aaaaa-7132-11e5-935b-c52d8a2aaaaa'}}

    cl = Route53Client(boto_client=TestBotoClient())
    zones = cl.list_zones()
    assert len(zones) == 2
    z1, z2 = zones
    assert z1.id == '/hostedzone/AAAA2A51Y0AAAA'
    assert z1.name == 'example.com.'
    assert z1.comment == None
    assert z1.rrs_count == 4
    assert z2.id == '/hostedzone/AAAAX6KE0IAAAA'
    assert z2.name == 'example.net.'
    assert z2.comment == 'Lorem ipsum'
    assert z2.rrs_count == 7
