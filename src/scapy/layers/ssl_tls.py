#! /usr/bin/env python
# -*- coding: UTF-8 -*-
# Author : tintinweb@oststrom.com <github.com/tintinweb>
# http://www.secdev.org/projects/scapy/doc/build_dissect.html
from scapy.packet import Packet, bind_layers
from scapy.fields import *
from scapy.layers.inet import TCP, UDP
import os, time

class BLenField(LenField):
    def __init__(self, name, default, fmt = "I", adjust=lambda pkt,x:x, numbytes=None, length_of=None, count_of=None):
        self.name = name
        self.adjust=adjust
        self.numbytes=numbytes
        self.length_of= length_of
        self.count_of = count_of
        LenField.__init__(self, name, default, fmt)

        if fmt[0] in "@=<>!":
            self.fmt = fmt
        else:
            self.fmt = "!"+fmt
        self.default = self.any2i(None,default)
        self.sz = struct.calcsize(self.fmt) if not numbytes else numbytes
        self.owners = []
        
    def addfield(self, pkt, s, val):
        """Add an internal value  to a string"""
        pack = struct.pack(self.fmt, self.i2m(pkt,val))
        if self.numbytes:
            pack=pack[len(pack)-self.numbytes:]
        return s+pack
    def getfield(self, pkt, s):
        """Extract an internal value from a string"""
        upack_data = s[:self.sz]
        # prepend struct.calcsize()-len(data) bytes to satisfy struct.unpack
        upack_data = '\x00'*(struct.calcsize(self.fmt)-self.sz) + upack_data
            
        return  s[self.sz:], self.m2i(pkt, struct.unpack(self.fmt, upack_data)[0])
    
    def i2m(self, pkt, x):
        if x is None:
            if not (self.length_of or self.count_of):
                 x = len(pkt.payload)
                 x = self.adjust(pkt,x)
                 return x
             
            if self.length_of is not None:
                fld,fval = pkt.getfield_and_val(self.length_of)
                f = fld.i2len(pkt, fval)
            else:
                fld,fval = pkt.getfield_and_val(self.count_of)
                f = fld.i2count(pkt, fval)
            x = self.adjust(pkt,f)
        return x

class XBLenField(BLenField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))
    
class XLenField(LenField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))
    
class XFieldLenField(FieldLenField):
    def i2repr(self, pkt, x):
        return lhex(self.i2h(pkt, x))    

TLS_VERSIONS = {0x0300:"SSL_3_0",
                  0x0301:"TLS_1_0",
                  0x0302:"TLS_1_1",
                  0x0303:"TLS_1_2",
                  
                  0x0100:"PROTOCOL_DTLS_1_0_OPENSSL_PRE_0_9_8f",
                  0xfeff:"DTLS_1_0",
                  0xfefd:"DTLS_1_1",
                  
                  }


TLS_CONTENT_TYPES = {0x14:"change_cipher_spec",
                        0x15:"alert",
                        0x16:"handshake",
                        0x17:"application_data",
                        0x18:"heartbeat",
                        0xff:"unknown"}

TLS_HANDSHAKE_TYPES = {0x00:"hello_request",
                        0x01:"client_hello",
                        0x02:"server_hello",
                        0x0b:"certificate",
                        0x0c:"server_key_exchange",
                        0x0d:"certificate_request",
                        0x0e:"server_hello_done",
                        0x0f:"certificate_verify",
                        0x10:"client_key_exchange",
                        0x20:"finished",
                        0x21:"certificate_url",
                        0x22:"certificate_stats",
                        0xff:"unknown"}

TLS_EXTENSION_TYPES = {
                       0x0000:"server_name",
                       0x0001:"max_fragment_length",
                       0x0002:"client_certificate_url",
                       0x0003:"trusted_ca_keys",
                       0x0004:"truncated_hmac",
                       0x0005:"status_request",
                       0x000a:"elliptic_curves",
                       0x000b:"ec_point_formats",
                       0x000d:"signature_algorithms",
                       0x000f:"heartbeat",
                       0x0023:"session_ticket_tls",
                       0x3374:"next_protocol_negotiation",
                       0xff01:"renegotiationg_info",
                       }

TLS_ALERT_LEVELS = { 0x01: "warning",
                     0x02: "fatal",
                     0xff: "unknown",}

TLS_ALERT_DESCRIPTIONS = {    
                    0:"CLOSE_NOTIFY",
                    10:"UNEXPECTE_MESSAGE",
                    20:"BAD_RECORD_MAC",
                    21:"DESCRIPTION_FAILED_RESERVED",
                    22:"RECORD_OVERFLOW",
                    30:"DECOMPRESSION_FAILURE",
                    40:"HANDSHAKE_FAILURE",
                    41:"NO_CERTIFICATE_RESERVED",
                    43:"BAD_CERTIFICATE",
                    43:"UNSUPPORTED_CERTIFICATE",
                    44:"CERTIFICATE_REVOKED",
                    45:"CERTIFICATE_EXPIRED",
                    46:"CERTIFICATE_UNKNOWN",
                    47:"ILLEGAL_PARAMETER",
                    48:"UNKNOWN_CA",
                    49:"ACCESS_DENIED",
                    50:"DECODE_ERROR",
                    51:"DECRYPT_ERROR",
                    60:"EXPORT_RESTRICTION_RESERVED",
                    70:"PROTOCOL_VERSION",
                    71:"INSUFFICIENT_SECURITY",
                    86:"INAPPROPRIATE_FALLBACK",
                    80:"INTERNAL_ERROR",
                    90:"USER_CANCELED",
                    100:"NO_RENEGOTIATION",
                    110:"UNSUPPORTED_EXTENSION",
                    111:"CERTIFICATE_UNOBTAINABLE",
                    112:"UNRECOGNIZED_NAME",
                    113:"BAD_CERTIFICATE_STATUS_RESPNSE",
                    114:"BAD_CERTIFICATE_HASH_VALUE",
                    255:"UNKNOWN_255",}

TLS_EXT_MAX_FRAGMENT_LENGTH_ENUM = {
                                    0x01: 2**9,
                                    0x02: 2**10,
                                    0x03: 2**11,
                                    0x04: 2**12,
                                    0xff: 'unknown',
                                    }


class TLSCipherSuite:
    '''
    make ciphersuites available as class props (autocompletion)
    '''
    NULL_WITH_NULL_NULL = 0x0000
    RSA_WITH_NULL_MD5 = 0x0001
    RSA_WITH_NULL_SHA1 = 0x0002
    RSA_WITH_NULL_SHA256 = 0x003b
    RSA_WITH_3DES_EDE_CBC_SHA =  0x000a
    DHE_RSA_WITH_3DES_EDE_CBC_SHA  = 0x0016    
    DHE_DSS_WITH_3DES_EDE_CBC_SHA  = 0x0013
    RSA_WITH_3DES_EDE_CBC_SHA =  0x000a
    DHE_RSA_WITH_AES_128_CBC_SHA  =  0x0033
    DHE_DSS_WITH_AES_128_CBC_SHA  = 0x0032
    RSA_WITH_AES_128_CBC_SHA = 0x002f
    RSA_WITH_IDEA_CBC_SHA  = 0x0007
    DHE_DSS_WITH_RC4_128_SHA  = 0x0066
    RSA_WITH_RC4_128_SHA  = 0x0005
    RSA_WITH_RC4_128_MD5  = 0x0004
    DHE_DSS_EXPORT1024_WITH_DES_CBC_SHA  = 0x0063
    RSA_EXPORT1024_WITH_DES_CBC_SHA  = 0x0062
    RSA_EXPORT1024_WITH_RC2_CBC_56_MD5  = 0x0061
    DHE_RSA_WITH_DES_CBC_SHA  = 0x0015
    DHE_DSS_WITH_DES_CBC_SHA  = 0x0012
    RSA_WITH_DES_CBC_SHA  = 0x0009
    DHE_DSS_EXPORT1024_WITH_RC4_56_SHA  = 0x0065
    RSA_EXPORT1024_WITH_RC4_56_SHA  = 0x0064
    RSA_EXPORT1024_WITH_RC4_56_MD5  = 0x0060
    DHE_RSA_EXPORT_WITH_DES40_CBC_SHA  = 0x0014
    DHE_DSS_EXPORT_WITH_DES40_CBC_SHA  = 0x0011
    RSA_EXPORT_WITH_DES40_CBC_SHA  = 0x0008
    RSA_EXPORT_WITH_RC2_CBC_40_MD5  = 0x0006
    RSA_EXPORT_WITH_RC4_40_MD5  = 0x0003
    RSA_WITH_AES_256_CBC_SHA = 0x0035
    DHE_DSS_WITH_AES_256_CBC_SHA = 0x0038    
    DHE_RSA_WITH_AES_256_CBC_SHA = 0x0039
    ECDHE_ECDSA_WITH_AES_256_CBC_SHA = 0xc00a
    ECDH_RSA_WITH_AES_256_CBC_SHA = 0xc00f    
    ECDHE_RSA_WITH_AES_256_CBC_SHA  = 0xc014
    SRP_SHA_RSA_WITH_AES_256_CBC_SHA = 0xc021
    SRP_SHA_DSS_WITH_AES_256_CBC_SHA = 0xc022
    DHE_DSS_WITH_CAMELLIA_256_CBC_SHA = 0x0087
    DHE_RSA_WITH_CAMELLIA_256_CBC_SHA = 0x0088
    ECDH_ECDSA_WITH_AES_256_CBC_SHA =0xc005
    RSA_WITH_CAMELLIA_256_CBC_SHA = 0x0084
    TLS_FALLBACK_SCSV = 0x5600
    
TLS_CIPHER_SUITES = dict((v,k) for k,v in TLSCipherSuite.__dict__.items() if not k.startswith("__"))

class TLSCompressionMethod:
    '''
    make compression methods available as class props (autocompletion)
    '''
    NULL = 0x00
    DEFLATE = 0x01
    
TLS_COMPRESSION_METHODS= dict((v,k) for k,v in TLSCompressionMethod.__dict__.items() if not k.startswith("__"))

class TLSRecord(Packet):
    name = "TLS Record"
    fields_desc = [ByteEnumField("content_type", 0xff, TLS_CONTENT_TYPES),
                   XShortEnumField("version", 0x0301, TLS_VERSIONS),
                   XLenField("length",None, fmt="!H"),]
    
class TLSHandshake(Packet):
    name = "TLS Handshake"
    fields_desc = [ByteEnumField("type", 0xff, TLS_HANDSHAKE_TYPES),
                   XBLenField("length",None, fmt="!I", numbytes=3),]


class TLSServerName(Packet):
    name = "TLS Servername"
    fields_desc = [ByteEnumField("type", 0x00, {0x00:"host"}),
                  XFieldLenField("length",None,length_of="data",fmt="H"),
                  StrLenField("data","",length_from=lambda x:x.length),
                  ]
    
class TLSServerNameIndication(Packet):
    name = "TLS Extension Servername Indication"
    fields_desc = [XFieldLenField("length",None,length_of="server_names",fmt="H"),
                   PacketListField("server_names",None,TLSServerName,length_from=lambda x:x.length),
                  ]

class TLSExtension(Packet):
    name = "TLS Extension"
    fields_desc = [XShortEnumField("type", 0x0000, TLS_EXTENSION_TYPES),
                   XLenField("length",None, fmt="!H"),
                  ]
#https://www.ietf.org/rfc/rfc3546.txt
class TLSExtMaxFragmentLength(Packet):
    name = "TLS Extension Max Fragment Length"
    fields_desc = [ByteEnumField("max_fragment_length", 0xff, TLS_EXT_MAX_FRAGMENT_LENGTH_ENUM)]
    
CERT_CHAIN_TYPE = { 0x00: 'individual_certs',
                    0x01: 'pkipath',
                    0xff: 'unknown'}
TLS_TYPE_BOOLEAN = {0x00: 'false',
                    0x01: 'true'}

class TLSURLAndOptionalHash(Packet):
    name = "TLS Extension Certificate URL/Hash"
    fields_desc = [XFieldLenField("url_length",None,length_of="url",fmt="H"),
                  StrLenField("url","",length_from=lambda x:x.url_length),
                  ByteEnumField("hash_present", 0x00, TLS_TYPE_BOOLEAN),
                  StrLenField("sha1hash","",length_from=lambda x:20 if x.hash_present else 0),    #opaque SHA1Hash[20];
                  ]
    
class TLSExtCertificateURL(Packet):
    name = "TLS Extension Certificate URL"
    fields_desc = [ByteEnumField("type", 0xff, CERT_CHAIN_TYPE),
                   XFieldLenField("length",None,length_of="server_names",fmt="H"),
                   PacketListField("certificate_urls",None,TLSURLAndOptionalHash,length_from=lambda x:x.length)
                   ]

    
class TLSClientHello(Packet):
    name = "TLS Client Hello"
    fields_desc = [XShortEnumField("version", 0x0301, TLS_VERSIONS),
                   IntField("gmt_unix_time",int(time.time())),
                   StrFixedLenField("random_bytes",os.urandom(28),28),
                   XFieldLenField("session_id_length",None,length_of="session_id",fmt="B"),
                   StrLenField("session_id",'',length_from=lambda x:x.session_id_length),
                   
                   XFieldLenField("cipher_suites_length",None,length_of="cipher_suites",fmt="H"),
                   FieldListField("cipher_suites",None,XShortEnumField("cipher",None,TLS_CIPHER_SUITES),length_from=lambda x:x.cipher_suites_length),
                   
                   XFieldLenField("compression_methods_length",None,length_of="compression_methods",fmt="B"),
                   FieldListField("compression_methods",None,ByteEnumField("compression",None,TLS_COMPRESSION_METHODS), length_from=lambda x:x.compression_methods_length),
                   
                   XFieldLenField("extensions_length",None,length_of="extensions",fmt="H"),
                   PacketListField("extensions",None,TLSExtension, length_from=lambda x:x.extension_length),
                   ]
    
class TLSServerHello(Packet):
    name = "TLS Server Hello"
    fields_desc = [XShortEnumField("version", 0x0301, TLS_VERSIONS),
                   IntField("gmt_unix_time",int(time.time())),
                   StrFixedLenField("random_bytes",os.urandom(28),28),
                   XFieldLenField("session_id_length",None,length_of="session_id",fmt="B"),
                   StrLenField("session_id",'',length_from=lambda x:x.session_id_length),

                   XShortEnumField("cipher_suite", 0x0000, TLS_CIPHER_SUITES),
                   ByteEnumField("compression_method", 0x00, TLS_COMPRESSION_METHODS),

                   XFieldLenField("extensions_length",None,length_of="extensions",fmt="H"),
                   PacketListField("extensions",None,TLSExtension, length_from=lambda x:x.extension_length),
                   ]

class TLSAlert(Packet):
    name = "TLS Alert"
    fields_desc = [ByteEnumField("level", 0xff, TLS_ALERT_LEVELS),
                  ByteEnumField("description", 0xff, TLS_ALERT_DESCRIPTIONS),
                  ]


class TLSHeartBeat(Packet):
    name = "TLS Extension HeartBeat"
    fields_desc = [ByteEnumField("type", 0x01, {0x01:"request"}),
                  FieldLenField("length",None,length_of="data",fmt="H"),
                  StrLenField("data","",length_from=lambda x:x.length),
                  StrLenField("padding","", length_from=lambda x: 'P'*(16-x.length)),
                  ]

class TLSServerKeyExchange(Packet):
    name = "TLS Server Key Exchange"
    fields_desc = [ XBLenField("length",None, fmt="!I", numbytes=3),
                    StrLenField("data",os.urandom(329),length_from=lambda x:x.length),]

class TLSDHServerParams(Packet):
    name = "TLS Diffie-Hellman Server Params"
    fields_desc = [XFieldLenField("p_length",None,length_of="p",fmt="!H"),
                   StrLenField("p",'',length_from=lambda x:x.p_length),
                   XFieldLenField("g_length",None,length_of="g",fmt="!H"),
                   StrLenField("g",'',length_from=lambda x:x.g_length),
                   XFieldLenField("pubkey_length",None,length_of="pubkey",fmt="!H"),
                   StrLenField("pubkey",'',length_from=lambda x:x.pubkey_length),
                   XFieldLenField("signature_length",None,length_of="signature",fmt="!H"),
                   StrLenField("signature",'',length_from=lambda x:x.signature_length),]
                   
class TLSServerHelloDone(Packet):
    name = "TLS Server Hello Done"
    fields_desc = [ XBLenField("length",None, fmt="!I", numbytes=3),
                    StrLenField("data","",length_from=lambda x:x.length),]
class TLSCertificate(Packet):
    name = "TLS Certificate"
    fields_desc = [ XBLenField("length",None, length_of="data", fmt="!I", numbytes=3),
                    StrLenField("data","",length_from=lambda x:x.length),]      #BERcodec_Object.dec(data,context=ASN1_Class_X509)
    
class TLSCertificateList(Packet):
    name = "TLS Certificate List"
    fields_desc = [
                   XBLenField("length",None,length_of="certificates",fmt="!I", numbytes=3),
                   PacketListField("certificates",None,TLSCertificate, length_from=lambda x:x.length),
                  ]   
    
    def do_dissect(self, s):
        pos=0
        #length field 
        self.length=struct.unpack("!I",'\x00'+s[:3])[0]
        pos += 3
        #certificate list
        cls = TLSCertificate
        cls_len=len(cls())
        try:
            while pos <=len(s):
                # consume payloads and add them to records list
                element = cls(s[pos:],_internal=1)         # FIXME: performance
                layer_len = cls_len + element.length
                if layer_len==None:
                    break
                element = cls(s[pos:pos+layer_len])
                pos+=layer_len
                #print pos,len(s)
                self.certificates.append(element)
        except Exception, e:
            pass
            #raise e
        return s[pos:]
        

class TLSChangeCipherSpec(Packet):
    name = "TLS ChangeCipherSpec"
    fields_desc = [ StrField("message",None, fmt="H")]


class DTLSRecord(Packet):
    name = "DTLS Record"
    fields_desc = [ByteEnumField("content_type", 0xff, TLS_CONTENT_TYPES),
                   XShortEnumField("version", 0x0301, TLS_VERSIONS),
                   ShortField("epoch",None),
                   XBLenField("sequence",None, fmt="!Q", numbytes=6),
                   XLenField("length",None, fmt="!H"),]

class DTLSHandshake(Packet):
    name = "DTLS Handshake"
    fields_desc = TLSHandshake.fields_desc+[
                   ShortField("sequence",None),
                   XBLenField("fragment_offset",None, fmt="!I", numbytes=3),
                   XBLenField("length",None, fmt="!I", numbytes=3),
                   ]

class DTLSClientHello(Packet):
    name = "DTLS Client Hello"
    fields_desc = [XShortEnumField("version", 0xfeff, TLS_VERSIONS),
                   IntField("gmt_unix_time",int(time.time())),
                   StrFixedLenField("random_bytes",os.urandom(28),28),
                   XFieldLenField("session_id_length",None,length_of="session_id",fmt="B"),
                   StrLenField("session_id",'',length_from=lambda x:x.session_id_length),
                   
                   XFieldLenField("cookie_length",None,length_of="cookie",fmt="B"),
                   StrLenField("cookie",'',length_from=lambda x:x.cookie_length),
                   
                   XFieldLenField("cipher_suites_length",None,length_of="cipher_suites",fmt="H"),
                   FieldListField("cipher_suites",None,XShortEnumField("cipher",None,TLS_CIPHER_SUITES),length_from=lambda x:x.cipher_suites_length),
                   
                   XFieldLenField("compression_methods_length",None,length_of="compression_methods",fmt="B"),
                   FieldListField("compression_methods",None,ByteEnumField("compression",None,TLS_COMPRESSION_METHODS), length_from=lambda x:x.compression_methods_length),
                   
                   XFieldLenField("extensions_length",None,length_of="extensions",fmt="H"),
                   PacketListField("extensions",None,TLSExtension, length_from=lambda x:x.extension_length),
                   ]   
    

class DTLSHelloVerify(Packet):
    name = "DTLS Hello Verify"
    fields_desc = [XShortEnumField("version", 0xfeff, TLS_VERSIONS),
                   XFieldLenField("cookie_length",None,length_of="cookie",fmt="B"),
                   StrLenField("cookie",'',length_from=lambda x:x.cookie_length),
                   ]
# entry class
class SSL(Packet):
    '''
    COMPOUND CLASS for SSL
    '''
    name = "SSL/TLS"
    fields_desc = [PacketListField("records",None,TLSRecord)]
    
    def pre_dissect(self, s):
        # figure out if we're UDP or TCP
        
        if self.underlayer and self.underlayer.haslayer(UDP):
            self.guessed_next_layer = DTLSRecord
        else:
            self.guessed_next_layer = TLSRecord
        self.fields_desc=[PacketListField("records",None,self.guessed_next_layer)]
        return s

    def do_dissect(self, s):
        pos = 0
        cls = self.guessed_next_layer                        # FIXME: detect DTLS
        cls_len=len(cls())
        try:
            while pos <=len(s):
            # consume payloads and add them to records list
                record = cls(s[pos:],_internal=1)         # FIXME: performance
                layer_len = cls_len + record.length
                if layer_len==None:
                    break
                record = cls(s[pos:pos+layer_len])
                pos+=layer_len
                #print pos,len(s)
                self.records.append(record)
        except Exception, e:
            pass
            #raise e
        return s[pos:]


# bind magic
bind_layers(TCP, SSL, dport=443)
bind_layers(TCP, SSL, sport=443)
bind_layers(UDP, SSL, dport=4433)
bind_layers(UDP, SSL, sport=4433)

# TLSRecord
bind_layers(TLSRecord, TLSChangeCipherSpec, {'content_type':0x14})
bind_layers(TLSRecord, TLSHeartBeat, {'content_type':0x18})
bind_layers(TLSRecord, TLSAlert, {'content_type':0x15})

bind_layers(TLSRecord, TLSHandshake, {'content_type':0x16})
# --> handshake proto
bind_layers(TLSHandshake,TLSClientHello, {'type':0x01})
bind_layers(TLSHandshake,TLSServerHello, {'type':0x02})
bind_layers(TLSHandshake,TLSCertificateList, {'type':0x0b})
# <---

# --> extensions
bind_layers(TLSExtension,TLSServerNameIndication, {'type': 0x0000})
bind_layers(TLSExtension,TLSExtMaxFragmentLength, {'type': 0x0001})
bind_layers(TLSExtension,TLSExtCertificateURL, {'type': 0x0002})
# <--


# DTLSRecord
bind_layers(DTLSRecord, DTLSHandshake, {'content_type':0x16})
bind_layers(DTLSHandshake, DTLSClientHello, {'type':0x01})
