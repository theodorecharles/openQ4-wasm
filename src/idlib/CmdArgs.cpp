



/*
============
idCmdArgs::operator=
============
*/
void idCmdArgs::operator=( const idCmdArgs &args ) {
	int i;

	argc = args.argc;
	memcpy( tokenized, args.tokenized, MAX_COMMAND_STRING );
	for ( i = 0; i < argc; i++ ) {
		argv[ i ] = tokenized + ( args.argv[ i ] - args.tokenized );
	}
}

/*
============
idCmdArgs::Args
============
*/
const char *idCmdArgs::Args(  int start, int end, bool escapeArgs ) const {
	static idStr cmd_args;
	int		i;

	if ( start < 0 ) {
		start = 0;
	}
	if ( end < 0 ) {
		end = argc - 1;
	} else if ( end >= argc ) {
		end = argc - 1;
	}
	cmd_args.Clear();
	if ( escapeArgs ) {
		cmd_args += "\"";
	}
	for ( i = start; i <= end; i++ ) {
		if ( i > start ) {
			if ( escapeArgs ) {
				cmd_args += "\" \"";
			} else {
				cmd_args += " ";
			}
		}
		if ( escapeArgs && strchr( argv[i], '\\' ) ) {
			char *p = argv[i];
			while ( *p != '\0' ) {
				if ( *p == '\\' ) {
					cmd_args += "\\\\";
				} else {
					cmd_args += *p;
				}
				p++;
			}
		} else {
			cmd_args += argv[i];
		}
	}
	if ( escapeArgs ) {
		cmd_args += "\"";
	}

	return cmd_args.c_str();
}

/*
============
idCmdArgs::TokenizeString

Parses the given string into command line tokens.
The text is copied to a separate buffer and 0 characters
are inserted in the appropriate place. The argv array
will point into this temporary buffer.
============
*/
void idCmdArgs::TokenizeString( const char *text, bool keepAsStrings ) {
	idLexer		lex;
	idToken		token, number;
	int			len, totalLen;

	// clear previous args
	argc = 0;

	if ( !text ) {
		return;
	}

	lex.LoadMemory( text, idLib::SizeToInt( strlen( text ), "idCmdArgs::TokenizeString" ), "idCmdSystemLocal::TokenizeString" );
	lex.SetFlags( LEXFL_NOERRORS
				| LEXFL_NOWARNINGS
				| LEXFL_NOSTRINGCONCAT
				| LEXFL_ALLOWPATHNAMES
				| LEXFL_NOSTRINGESCAPECHARS
				| LEXFL_ALLOWIPADDRESSES | ( keepAsStrings ? LEXFL_ONLYSTRINGS : 0 ) );

	totalLen = 0;

	while ( 1 ) {
		if ( argc == MAX_COMMAND_ARGS ) {
			return;			// this is usually something malicious
		}

		if ( !lex.ReadToken( &token ) ) {
			return;
		}

		// check for negative numbers
		if ( !keepAsStrings && ( token == "-" ) ) {
			if ( lex.CheckTokenType( TT_NUMBER, 0, &number ) ) {
				token = "-" + number;
			}
		}

		// check for cvar expansion
		if ( token == "$" ) {
			if ( !lex.ReadToken( &token ) ) {
				return;
			}
			if ( idLib::cvarSystem ) {
				token = idLib::cvarSystem->GetCVarString( token.c_str() );
			} else {
				token = "<unknown>";
			}
		}

		len = token.Length();

		if ( totalLen + len + 1 > sizeof( tokenized ) ) {
			return;			// this is usually something malicious
		}

		// regular token
		argv[argc] = tokenized + totalLen;
		argc++;

		idStr::Copynz( tokenized + totalLen, token.c_str(), sizeof( tokenized ) - totalLen );

		totalLen += len + 1;
	}
}
/*
============
idCmdArgs::AppendArg
============
*/
void idCmdArgs::AppendArg( const char *text ) {
	if ( !text ) {
		text = "";
	}

	// Harden against malformed command-line input paths that might feed
	// pathological token counts into a single command.
	if ( argc < 0 || argc > MAX_COMMAND_ARGS ) {
		argc = 0;
	}

	if ( argc == 0 ) {
		argv[ 0 ] = tokenized;
		idStr::Copynz( tokenized, text, sizeof( tokenized ) );
		argc = 1;
		return;
	}

	if ( argc >= MAX_COMMAND_ARGS ) {
		return;
	}

	char *next = argv[ argc - 1 ] + strlen( argv[ argc - 1 ] ) + 1;
	if ( next < tokenized || next >= tokenized + sizeof( tokenized ) ) {
		return;
	}

	const size_t used = static_cast<size_t>( next - tokenized );
	const int remaining = idLib::SizeToInt( sizeof( tokenized ) - used, "idCmdArgs::AppendArg" );
	argv[ argc ] = next;
	idStr::Copynz( argv[ argc ], text, remaining );
	argc++;
}

/*
============
idCmdArgs::GetArgs
============
*/
const char **idCmdArgs::GetArgs( int *_argc ) {
	*_argc = argc;
	return (const char **)&argv[0];
}

