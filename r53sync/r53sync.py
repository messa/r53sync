
import sys

from .route53 import Route53Client


class R53Sync:
    '''
    This class contains main functionality.
    Method functions correspond to CLI commands.
    '''

    def __init__(self, boto_client=None, stdout=None):
        self.r53_client = Route53Client(boto_client=boto_client)
        self.text_if = TextInterface(stdout=stdout)

    def list_zones(self):
        zones = self.r53_client.list_zones()
        self.text_if.print_zone_table(zones)

    def list_zone_records(self, zone_name):
        rrsets = self.r53_client.list_zone_rrsets(zone_name)
        print_rrset_table(rrsets)


class TextInterface:

    def __init__(self, stdout=None):
        self.stdout = stdout if stdout else sys.stdout

    def _print(self, s='', *args, **kwargs):
        assert isinstance(s, str), repr(s)
        print(s.format(*args, **kwargs), file=self.stdout)

    def print_zone_table(self, zones):
        pr = self._print
        pr('name                                count id                          comment')
        pr('----------------------------------- ----- --------------------------- ---------------------------------')
        for z in zones:
            pr('{z.name:35} {z.rrs_count:5} {z.id:27} {comment}', z=z,
                comment='-' if z.comment is None else z.comment)

    def print_rrset_table(self, rrsets):
        pr = self._print
        pr('Name                                Type     TTL Info')
        pr('----------------------------------- ----- ------ ------------------------------------------------------')
        for rrs in rrsets:
            info = []
            if rrs.get('AliasTarget'):
                info.append('alias: {}'.format(rrs['AliasTarget']['DNSName']))
            if rrs.get('ResourceRecords'):
                assert isinstance(rrs['ResourceRecords'], list), repr(rrs['ResourceRecords'])
                for rec in rrs['ResourceRecords']:
                    if set(rec.keys()) == {'Value'}:
                        info.append(rec['Value'])
                    else:
                        info.append(repr(rec))

            print('{:35} {:5} {:>6} {}', rrs['Name'], rrs['Type'], rrs.get('TTL', '-'), ', '.join(info))
