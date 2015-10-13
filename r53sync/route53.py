import boto3
import logging

from .model import hosted_zone_from_aws


logger = logging.getLogger(__name__)


class Route53Client:
    '''
    Wraps boto3 API into something more comfortable (with automatic paging).
    Methods return model objects instead of plain dicts.
    '''

    def __init__(self, boto_client=None):
        self._client = boto_client
        self.logger = logger
        self._zone_name_id_cache = {}

    @property
    def client(self):
        '''
        Boto3 client
        '''
        if not self._client:
            # we want lazy instantiation of real Boto client
            self._client = boto3.client('route53')
            assert self._client
        return self._client

    def get_zone_id_from_name(self, zone_name):
        if zone_name not in self._zone_name_id_cache:
            self._zone_name_id_cache[zone_name] = self._do_get_zone_id_from_name(zone_name)
        return self._zone_name_id_cache[zone_name]

    def _do_get_zone_id_from_name(self, zone_name):
        result = self.client.list_hosted_zones_by_name(DNSName=zone_name, MaxItems='1')
        hzs = [hz for hz in result['HostedZones'] if hz['Name'] == zone_name]
        if not hzs:
            raise Exception('Hosted zone {!r} not found'.format(zone_name))
        if len(hzs) > 1:
            # should not happen
            raise Exception('More than 1 hosted zone found for name {!r}'.format(zone_name))
        hz, = hzs
        self.logger.debug('Zone %r has id %r', zone_name, hz['Id'])
        zone_id = hz['Id']
        assert isinstance(zone_id, str)
        return zone_id

    def list_zones(self):
        raw_hzs = []
        extra_kwargs = {}
        while True:
            result = self.client.list_hosted_zones(**extra_kwargs)
            raw_hzs.extend(result['HostedZones'])
            if result.get('IsTruncated'):
                extra_kwargs = {
                    'Marker': result['NextMarker'],
                }
                continue
            else:
                break
        return [hosted_zone_from_aws(raw_hz) for raw_hz in raw_hzs]

    def list_zone_rrsets(self, zone_name):
        zone_id = self.get_zone_id_from_name(zone_name)
        all_rrsets = []
        extra_kwargs = {}
        while True:
            self.logger.debug('list_resource_record_sets %r %r', zone_id, extra_kwargs)
            result = self.client.list_resource_record_sets(HostedZoneId=zone_id, MaxItems='100', **extra_kwargs)
            all_rrsets.extend(result['ResourceRecordSets'])
            if result.get('IsTruncated'):
                extra_kwargs = {
                    'StartRecordName': result['NextRecordName'],
                    'StartRecordType': result['NextRecordType'],
                }
                if result.get('NextRecordIdentifier'):
                    extra_kwargs['StartRecordIdentifier'] = result['NextRecordIdentifier']
                continue
            else:
                break
        return all_rrsets

    def create(self, zone_name, record_name, record_type, values, alias):
        assert record_name.endswith('.')
        assert values is None or alias is None
        assert values or alias
        zone_id = self.get_zone_id_from_name(zone_name)
        new_rrs = {
            'Name': record_name,
            'Type': record_type,
        }
        if values:
            assert all(isinstance(v, str) for v in values)
            new_rrs['ResourceRecords'] = [{'Value': v} for v in values]
            new_rrs['TTL'] = 1800
        if alias:
            assert isinstance(alias, str)
            new_rrs['AliasTarget'] = {
                'DNSName': alias,
            }
        chb = {
            'Comment': 'r53sync {dt}'.format(dt=datetime.utcnow()),
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': new_rrs,
                },
            ],
        }
        print('Sending change batch:', chb)
        self.client.change_resource_record_sets(
            HostedZoneId=zone_id,
            ChangeBatch=chb)
