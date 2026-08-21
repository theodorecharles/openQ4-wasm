#include "src/idlib/NumericString.h"
#include "src/idlib/StrAllocation.h"
#include "src/sys/NetworkEndpoint.h"

#include <climits>
#include <cstdio>
#include <limits>

static int failures = 0;

static void ExpectDecimal( const char *text, const bool expected, const char *label ) {
	const bool actual = idNumericString::IsDecimal( text );
	if ( actual != expected ) {
		std::fprintf( stderr, "IsDecimal failed for %s: expected %d, got %d\n", label, expected, actual );
		failures++;
	}
}

static void ExpectBounded( const char *text, const int maximum, const bool expected,
		const int expectedValue, const char *label ) {
	int value = -7331;
	const bool actual = idNumericString::ParseUnsignedBounded( text, maximum, value );
	if ( actual != expected ) {
		std::fprintf( stderr, "ParseUnsignedBounded failed for %s: expected %d, got %d\n", label, expected, actual );
		failures++;
		return;
	}
	if ( actual && value != expectedValue ) {
		std::fprintf( stderr, "ParseUnsignedBounded value failed for %s: expected %d, got %d\n", label, expectedValue, value );
		failures++;
	}
	if ( !actual && value != -7331 ) {
		std::fprintf( stderr, "ParseUnsignedBounded modified output on failure for %s\n", label );
		failures++;
	}
}

static void ExpectAllocation( const bool condition, const char *label ) {
	if ( !condition ) {
		std::fprintf( stderr, "String allocation arithmetic failed for %s\n", label );
		failures++;
	}
}

static void ExpectEndpoint( const char *text, const bool expected, const char *expectedHost,
		const bool expectedHasPort, const unsigned short expectedPort, const char *label ) {
	char host[256] = "untouched";
	idNetworkEndpoint::endpointParts_t parts;
	const bool actual = idNetworkEndpoint::Split( text, host, sizeof( host ), parts );
	if ( actual != expected ) {
		std::fprintf( stderr, "Network endpoint split failed for %s: expected %d, got %d\n", label, expected, actual );
		failures++;
		return;
	}
	if ( !actual ) {
		if ( host[0] != '\0' || parts.hasPort || parts.port != 0 ) {
			std::fprintf( stderr, "Network endpoint split left output on failure for %s\n", label );
			failures++;
		}
		return;
	}
	if ( std::strcmp( host, expectedHost ) != 0 || parts.hasPort != expectedHasPort || parts.port != expectedPort ) {
		std::fprintf(
			stderr,
			"Network endpoint split value failed for %s: got host='%s', hasPort=%d, port=%u\n",
			label,
			host,
			parts.hasPort,
			static_cast<unsigned int>( parts.port )
		);
		failures++;
	}
}

static void ParseIPv6Hex( const char *hex, unsigned char out[16] ) {
	for ( int i = 0; i < 16; i++ ) {
		int value = 0;
		for ( int nibble = 0; nibble < 2; nibble++ ) {
			const char digit = hex[i * 2 + nibble];
			int parsed = 0;
			if ( digit >= '0' && digit <= '9' ) {
				parsed = digit - '0';
			} else if ( digit >= 'a' && digit <= 'f' ) {
				parsed = digit - 'a' + 10;
			} else if ( digit >= 'A' && digit <= 'F' ) {
				parsed = digit - 'A' + 10;
			}
			value = ( value << 4 ) | parsed;
		}
		out[i] = static_cast<unsigned char>( value );
	}
}

static void ExpectIPv6Text( const char *hex, const char *expected, const char *label ) {
	unsigned char ip6[16];
	ParseIPv6Hex( hex, ip6 );
	char text[idNetworkEndpoint::IPV6_TEXT_SIZE];
	if ( !idNetworkEndpoint::FormatIPv6( ip6, text, sizeof( text ) ) ) {
		std::fprintf( stderr, "IPv6 formatting failed for %s\n", label );
		failures++;
		return;
	}
	if ( std::strcmp( text, expected ) != 0 ) {
		std::fprintf( stderr, "IPv6 formatting value failed for %s: expected '%s', got '%s'\n", label, expected, text );
		failures++;
	}
}

static void ExpectIPv6Endpoint( const char *hex, const unsigned int scopeId, const unsigned short port,
		const char *expected, const char *label ) {
	unsigned char ip6[16];
	ParseIPv6Hex( hex, ip6 );
	char text[idNetworkEndpoint::IPV6_ENDPOINT_TEXT_SIZE];
	if ( !idNetworkEndpoint::FormatIPv6Endpoint( ip6, scopeId, port, text, sizeof( text ) ) ) {
		std::fprintf( stderr, "IPv6 endpoint formatting failed for %s\n", label );
		failures++;
		return;
	}
	if ( std::strcmp( text, expected ) != 0 ) {
		std::fprintf( stderr, "IPv6 endpoint value failed for %s: expected '%s', got '%s'\n", label, expected, text );
		failures++;
	}
}

static void ExpectLocalServerEndpoint( const char *netIP, const int netPort, const bool expected,
		const char *expectedText, const char *label ) {
	// Sized for interface text, which may be a host name, not for an address
	// literal - the same distinction the callers have to make.
	char text[idNetworkEndpoint::LOCAL_ENDPOINT_TEXT_SIZE] = "untouched";
	const bool actual = idNetworkEndpoint::FormatLocalServerEndpoint( netIP, netPort, text, sizeof( text ) );
	if ( actual != expected ) {
		std::fprintf( stderr, "Local server endpoint failed for %s: expected %d, got %d\n", label, expected, actual );
		failures++;
		return;
	}
	if ( !actual ) {
		if ( text[0] != '\0' ) {
			std::fprintf( stderr, "Local server endpoint left output on failure for %s\n", label );
			failures++;
		}
		return;
	}
	if ( std::strcmp( text, expectedText ) != 0 ) {
		std::fprintf( stderr, "Local server endpoint value failed for %s: expected '%s', got '%s'\n", label, expectedText, text );
		failures++;
	}
}

static void ExpectBindPlan( const char *ipv4Text, const char *ipv6Text, const bool enableIPv4, const bool enableIPv6,
		const bool expectIPv4, const bool expectIPv6, const char *expectedIPv6Interface, const char *label ) {
	idNetworkEndpoint::bindPlan_t plan;
	idNetworkEndpoint::PlanBind( ipv4Text, ipv6Text, enableIPv4, enableIPv6, plan );
	if ( plan.bindIPv4 != expectIPv4 || plan.bindIPv6 != expectIPv6 ) {
		std::fprintf( stderr, "Bind plan families failed for %s: got v4=%d v6=%d\n", label, plan.bindIPv4, plan.bindIPv6 );
		failures++;
		return;
	}
	const char *actualIPv6 = plan.ipv6Interface != nullptr ? plan.ipv6Interface : "";
	if ( std::strcmp( actualIPv6, expectedIPv6Interface ) != 0 ) {
		std::fprintf( stderr, "Bind plan IPv6 interface failed for %s: expected '%s', got '%s'\n",
			label, expectedIPv6Interface, actualIPv6 );
		failures++;
	}
}

int main() {
	const char *validDecimals[] = {
		"0", "-0", "123", "-123", "1.0", ".5", "-.5", "5."
	};
	for ( const char *value : validDecimals ) {
		ExpectDecimal( value, true, value );
	}

	const char *invalidDecimals[] = {
		"", "-", ".", "-.", "+1", "1..0", "1e3", " 1", "1 ", "--1", "one"
	};
	ExpectDecimal( nullptr, false, "null" );
	for ( const char *value : invalidDecimals ) {
		ExpectDecimal( value, false, value[ 0 ] == '\0' ? "empty" : value );
	}

	ExpectBounded( "0", 127, true, 0, "zero" );
	ExpectBounded( "127", 127, true, 127, "maximum" );
	ExpectBounded( "000127", 127, true, 127, "leading zeroes" );
	ExpectBounded( "128", 127, false, 0, "one above maximum" );
	ExpectBounded( "999999999999999999999999999999", 127, false, 0, "overflow-sized input" );
	ExpectBounded( "", 127, false, 0, "empty" );
	ExpectBounded( nullptr, 127, false, 0, "null" );
	ExpectBounded( "-1", 127, false, 0, "negative" );
	ExpectBounded( "12x", 127, false, 0, "non-digit" );
	ExpectBounded( "0", -1, false, 0, "negative maximum" );

	using namespace idStrAllocationDetail;
	const size_t sizeMaximum = ( std::numeric_limits<size_t>::max )();
	ExpectAllocation( SaturatingAdd( 17, 25 ) == 42, "ordinary addition" );
	ExpectAllocation( SaturatingAdd( sizeMaximum, 1 ) == sizeMaximum, "saturating addition" );
	ExpectAllocation( SaturatingMultiply( 6, 7 ) == 42, "ordinary multiplication" );
	ExpectAllocation( SaturatingMultiply( sizeMaximum, 2 ) == sizeMaximum, "saturating multiplication" );

	int roundedAmount = 0;
	const size_t maximumRoundedAllocation = static_cast<size_t>( INT_MAX ) / 32 * 32;
	ExpectAllocation( TryRoundUpToInt( 1, 32, roundedAmount ) && roundedAmount == 32, "small round-up" );
	ExpectAllocation(
		TryRoundUpToInt( maximumRoundedAllocation, 32, roundedAmount ) &&
			roundedAmount == static_cast<int>( maximumRoundedAllocation ),
		"largest representable rounded allocation"
	);
	ExpectAllocation( !TryRoundUpToInt( maximumRoundedAllocation + 1, 32, roundedAmount ), "first unrepresentable round-up" );
	ExpectAllocation( !TryRoundUpToInt( static_cast<size_t>( INT_MAX ), 32, roundedAmount ), "INT_MAX round-up" );
	ExpectAllocation( !TryRoundUpToInt( sizeMaximum, 32, roundedAmount ), "SIZE_MAX round-up" );
	ExpectAllocation( !TryRoundUpToInt( 1, 0, roundedAmount ), "zero granularity" );

	ExpectEndpoint( "127.0.0.1", true, "127.0.0.1", false, 0, "numeric IPv4" );
	ExpectEndpoint( "127.0.0.1:65535", true, "127.0.0.1", true, 65535, "maximum IPv4 port" );
	ExpectEndpoint( "4.example.com:27960", true, "4.example.com", true, 27960, "digit-leading hostname" );
	ExpectEndpoint( "255.255.255.255", true, "255.255.255.255", false, 0, "IPv4 broadcast literal" );
	ExpectEndpoint( "hostname:0", true, "hostname", true, 0, "explicit zero port" );
	ExpectEndpoint( "::1", true, "::1", false, 0, "unbracketed IPv6 literal" );
	ExpectEndpoint( "[::1]:27960", true, "::1", true, 27960, "bracketed IPv6 endpoint" );
	ExpectEndpoint( "[fe80::1%3]", true, "fe80::1%3", false, 0, "scoped IPv6 literal" );
	ExpectEndpoint( "fe80::1%eth0", true, "fe80::1%eth0", false, 0, "unbracketed named zone" );
	ExpectEndpoint( "[fe80::1%eth0]:27650", true, "fe80::1%eth0", true, 27650, "bracketed named zone" );
	ExpectEndpoint( "::ffff:1.2.3.4", true, "::ffff:1.2.3.4", false, 0, "IPv4-mapped literal" );
	ExpectEndpoint( "2001:db8::1", true, "2001:db8::1", false, 0, "unbracketed global unicast" );
	ExpectEndpoint( "[2001:db8::1]", true, "2001:db8::1", false, 0, "bracketed literal without a port" );
	ExpectEndpoint( "::", true, "::", false, 0, "unspecified address" );
	// Two or more colons and no brackets means the whole string is a host, so an
	// unbracketed scoped literal with a port is a host name the resolver will
	// reject rather than a silently mis-split endpoint.
	ExpectEndpoint( "fe80::1%eth0:27650", true, "fe80::1%eth0:27650", false, 0, "unbracketed scoped literal with a port" );

	ExpectIPv6Text( "00000000000000000000000000000000", "::", "unspecified" );
	ExpectIPv6Text( "00000000000000000000000000000001", "::1", "loopback" );
	ExpectIPv6Text( "20010db8000000000000000000000001", "2001:db8::1", "global unicast" );
	ExpectIPv6Text( "00010002000300040005000600070008", "1:2:3:4:5:6:7:8", "no zero groups" );
	ExpectIPv6Text( "fe800000000000000000000000000000", "fe80::", "trailing zero run" );
	// A single zero group is never compressed.
	ExpectIPv6Text( "20010000000100010001000100010001", "2001:0:1:1:1:1:1:1", "single zero group" );
	// The leftmost of two equally long runs wins.
	ExpectIPv6Text( "00010000000000020000000000030004", "1::2:0:0:3:4", "leftmost equal-length run" );
	// The longest run wins even when a shorter one comes first.
	ExpectIPv6Text( "00010000000000020000000000000003", "1:0:0:2::3", "longest run" );
	ExpectIPv6Text( "00000000000000000000ffff01020304", "::ffff:1.2.3.4", "IPv4-mapped dotted tail" );
	ExpectIPv6Text( "00000000000000000000ffffffffffff", "::ffff:255.255.255.255", "IPv4-mapped maximum" );
	// Only ::ffff:0:0/96 earns the dotted tail.
	ExpectIPv6Text( "ffffffffffffffffffffffff01020304", "ffff:ffff:ffff:ffff:ffff:ffff:102:304", "non-mapped tail" );
	ExpectIPv6Text( "ffffffffffffffffffffffffffffffff", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", "longest literal" );

	ExpectIPv6Endpoint( "00000000000000000000000000000001", 0, 0, "::1", "loopback without a port" );
	ExpectIPv6Endpoint( "00000000000000000000000000000001", 0, 27650, "[::1]:27650", "loopback with a port" );
	ExpectIPv6Endpoint( "fe800000000000000000000000000001", 12, 27650, "[fe80::1%12]:27650", "scoped endpoint" );
	ExpectIPv6Endpoint( "fe800000000000000000000000000001", 12, 0, "fe80::1%12", "scoped without a port" );
	ExpectIPv6Endpoint(
		"ffffffffffffffffffffffffffffffff", 4294967295u, 65535,
		"[ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff%4294967295]:65535", "longest endpoint" );

	{
		// A truncated address would alias two distinct servers onto one browser
		// key and one ban-list entry, so an undersized buffer must fail closed.
		unsigned char widest[16];
		ParseIPv6Hex( "ffffffffffffffffffffffffffffffff", widest );
		char tooSmall[8] = "keepme";
		if ( idNetworkEndpoint::FormatIPv6( widest, tooSmall, sizeof( tooSmall ) ) || tooSmall[0] != '\0' ) {
			std::fprintf( stderr, "IPv6 formatting accepted an undersized buffer\n" );
			failures++;
		}
		if ( idNetworkEndpoint::FormatIPv6( nullptr, tooSmall, sizeof( tooSmall ) ) ) {
			std::fprintf( stderr, "IPv6 formatting accepted a null address\n" );
			failures++;
		}
	}

	ExpectLocalServerEndpoint( "", 27650, true, "127.0.0.1:27650", "wildcard interface" );
	ExpectLocalServerEndpoint( nullptr, 0, false, "", "no interface and no port" );
	ExpectLocalServerEndpoint( "0.0.0.0", 27650, true, "127.0.0.1:27650", "IPv4 wildcard literal" );
	ExpectLocalServerEndpoint( "192.168.1.5", 27650, true, "192.168.1.5:27650", "explicit IPv4 interface" );
	ExpectLocalServerEndpoint( "::", 27650, true, "[::1]:27650", "IPv6 wildcard literal" );
	ExpectLocalServerEndpoint( "2001:db8::5", 27650, true, "[2001:db8::5]:27650", "bare IPv6 interface" );
	ExpectLocalServerEndpoint( "[2001:db8::5]", 27650, true, "[2001:db8::5]:27650", "bracketed IPv6 interface" );
	// "localhost" is the shipped net_ip default and names every interface, so
	// the endpoint shown is the loopback a player can actually dial.
	ExpectLocalServerEndpoint( "localhost", 27650, true, "127.0.0.1:27650", "default interface name" );
	// net_port 0 means "choose automatically"; the chosen port is not known
	// here, so naming it would point players at a port nothing listens on.
	ExpectLocalServerEndpoint( "localhost", 0, false, "", "default interface and automatic port" );
	ExpectLocalServerEndpoint( "192.168.1.5", 0, true, "192.168.1.5", "explicit interface, automatic port" );
	{
		// An interface may be a host name far longer than any address literal.
		const char *longHost = "gameserver-01.eu-west-2.datacenter.example-hosting-provider.com";
		char expected[idNetworkEndpoint::LOCAL_ENDPOINT_TEXT_SIZE];
		std::snprintf( expected, sizeof( expected ), "%s:28004", longHost );
		ExpectLocalServerEndpoint( longHost, 28004, true, expected, "long hostname interface" );
	}

	ExpectBindPlan( "localhost", "", true, true, true, true, "", "default dual-stack plan" );
	ExpectBindPlan( "192.168.1.5", "", true, true, true, true, "", "explicit IPv4 interface" );
	ExpectBindPlan( "192.168.1.5:27650", "", true, true, true, true, "", "IPv4 interface carrying a port" );
	ExpectBindPlan( "localhost", "2001:db8::5", true, true, true, true, "2001:db8::5", "explicit IPv6 interface" );
	ExpectBindPlan( "localhost", "", false, true, false, true, "", "IPv6-only host" );
	ExpectBindPlan( "localhost", "", true, false, true, false, "", "IPv4-only host" );
	// An IPv6 literal in net_ip is a pre-net_ip6 configuration, and has to keep
	// producing the single IPv6 socket it always did.
	ExpectBindPlan( "2001:db8::5", "", true, true, false, true, "2001:db8::5", "legacy IPv6 net_ip" );
	ExpectBindPlan( "2001:db8::5", "2001:db8::6", true, true, false, true, "2001:db8::6", "net_ip6 wins over legacy net_ip" );

	ExpectEndpoint( nullptr, false, "", false, 0, "null endpoint" );
	ExpectEndpoint( "", false, "", false, 0, "empty endpoint" );
	ExpectEndpoint( ":27960", false, "", false, 0, "missing host" );
	ExpectEndpoint( "host:", false, "", false, 0, "missing port" );
	ExpectEndpoint( "host:-1", false, "", false, 0, "negative port" );
	ExpectEndpoint( "host:65536", false, "", false, 0, "out-of-range port" );
	ExpectEndpoint( "host:184467440737095516160", false, "", false, 0, "overflowing decimal port" );
	ExpectEndpoint( "host:12x", false, "", false, 0, "non-numeric port" );
	ExpectEndpoint( "[::1", false, "", false, 0, "missing close bracket" );
	ExpectEndpoint( "[]:27960", false, "", false, 0, "empty bracketed host" );
	ExpectEndpoint( "[::1]junk", false, "", false, 0, "text after close bracket" );

	if ( failures != 0 ) {
		std::fprintf( stderr, "core safety native test: %d failure(s)\n", failures );
		return 1;
	}

	std::printf( "core safety native test: ok\n" );
	return 0;
}
