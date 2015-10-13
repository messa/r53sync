
from io import StringIO
from textwrap import dedent

from r53sync import R53Sync


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
    test_out = StringIO()
    test_boto_client = TestBotoClient()
    r53sync = R53Sync(stdout=test_out, boto_client=test_boto_client)
    r53sync.list_zones()
    out = test_out.getvalue()
    assert out == dedent('''
        name                                count id                          comment
        ----------------------------------- ----- --------------------------- ---------------------------------
        example.com.                            4 /hostedzone/AAAA2A51Y0AAAA  -
        example.net.                            7 /hostedzone/AAAAX6KE0IAAAA  Lorem ipsum
    ''').lstrip()


def test_list_zone_records():
    class TestBotoClient:

        def list_hosted_zones_by_name(self, **kwargs):
            assert kwargs == {'DNSName': 'example.com.', 'MaxItems': '1'}
            return {
                 'DNSName': 'example.com.',
                 'HostedZones': [{'CallerReference': '856AAAAA-E2F6-3E94-BA8E-B8AAAAAAAAAA',
                                  'Config': {'Comment': 'Lorem ipsum',
                                             'PrivateZone': False},
                                  'Id': '/hostedzone/Z1F7GAAAAAAAAS',
                                  'Name': 'example.com.',
                                  'ResourceRecordSetCount': 33}],
                 'IsTruncated': True,
                 'MaxItems': '1',
                 'NextDNSName': 'example.net.',
                 'NextHostedZoneId': 'Z1G4AAAAAAAAAA',
                 'ResponseMetadata': {'HTTPStatusCode': 200,
                                      'RequestId': '0a5aaaaa-7136-11e5-90fe-17e65aaaaaaa'}}

        def list_resource_record_sets(self, **kwargs):
            assert 0, kwargs
            return {
                 'IsTruncated': False,
                 'MaxItems': '100',
                 'ResourceRecordSets': [{'Name': 'example.com.',
                                         'ResourceRecords': [{'Value': '10.20.30.40'}],
                                         'TTL': 300,
                                         'Type': 'A'},
                                        {'Name': 'example.com.',
                                         'ResourceRecords': [{'Value': '5 '
                                                                       'ALT1.ASPMX.L.GOOGLE.COM.'},
                                                             {'Value': '1 '
                                                                       'ASPMX.L.GOOGLE.COM.'}],
                                         'TTL': 300,
                                         'Type': 'MX'},
                                        {'Name': 'example.com.',
                                         'ResourceRecords': [{'Value': 'ns-60.awsdns-07.com.'},
                                                             {'Value': 'ns-1390.awsdns-45.org.'},
                                                             {'Value': 'ns-657.awsdns-18.net.'},
                                                             {'Value': 'ns-2011.awsdns-59.co.uk.'}],
                                         'TTL': 172800,
                                         'Type': 'NS'},
                                        {'Name': 'example.com.',
                                         'ResourceRecords': [{'Value': 'ns-657.awsdns-18.net. '
                                                                       'awsdns-hostmaster.amazon.com. '
                                                                       '1 7200 900 '
                                                                       '1209600 86400'}],
                                         'TTL': 900,
                                         'Type': 'SOA'},
                                        {'Name': 'example.com.',
                                         'ResourceRecords': [{'Value': '"google-site-verification=dEAdbeef"'}],
                                         'TTL': 300,
                                         'Type': 'TXT'},
                                        {'Name': 'www.example.com.',
                                         'ResourceRecords': [{'Value': '10.20.30.55'}],
                                         'TTL': 3600,
                                         'Type': 'A'},
                                        {'Name': 'mail.example.com.',
                                         'ResourceRecords': [{'Value': 'www.example.com.'}],
                                         'TTL': 86400,
                                         'Type': 'CNAME'},
                                        {'AliasTarget': {'DNSName': 'www.example.com.',
                                                         'EvaluateTargetHealth': False,
                                                         'HostedZoneId': 'Z1F7GAAAAAAAAS'},
                                         'Name': 'www2.example.com.',
                                         'Type': 'A'},
                                        }],
                 'ResponseMetadata': {'HTTPStatusCode': 200,
                                      'RequestId': '6a6aaaa4-7136-11e5-9e8f-bbaaaaa1ada5'}}


    test_out = StringIO()
    test_boto_client = TestBotoClient()
    r53sync = R53Sync(stdout=test_out, boto_client=test_boto_client)
    r53sync.list_zone_records('example.com.')
    out = test_out.getvalue()
    assert out == dedent('''
        name                                count id                          comment
        ----------------------------------- ----- --------------------------- ---------------------------------
        example.com.                            4 /hostedzone/AAAA2A51Y0AAAA  -
        example.net.                            7 /hostedzone/AAAAX6KE0IAAAA  Lorem ipsum
    ''').lstrip()
