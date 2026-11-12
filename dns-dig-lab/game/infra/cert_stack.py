"""The TLS certificate of the game's own address. CloudFront only takes certificates from us-east-1,
so this small stack lives there; DigQuest (eu-west-3) reads it through a cross-region reference."""
from aws_cdk import Stack, aws_certificatemanager as acm, aws_route53 as route53
from constructs import Construct


class CertStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, domain: str, zone_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        # validated by DNS in the Route 53 zone that holds the name (it must already be in this account)
        zone = route53.HostedZone.from_lookup(self, "Zone", domain_name=zone_name)
        self.certificate = acm.Certificate(
            self, "Cert", domain_name=domain, validation=acm.CertificateValidation.from_dns(zone),
        )
