#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <errno.h>
#include <limits.h>
#include <malloc.h>
#include <unistd.h>
#include <sys/mman.h>

#define eprintf(format, ...) fprintf(stderr, "[%s:%d] [%s] " format, __FILE__, __LINE__, __PRETTY_FUNCTION__, ##__VA_ARGS__)

typedef std::pair<void*, size_t> memblock;

// the task of parsing the complex arguments will be left to python.

static const char* const cmds[] =
{
    "malloc",
    "calloc",
    "realloc",
    "free",
    "fopen",
    "fclose",
    "dump",
    "write",
    "list",
    "leak",
    "minfo",
    "mmap",
    NULL,
};

static const int cmd_count = sizeof ( cmds ) / sizeof ( cmds[0] ) - 1;

static const char* const sizes[] =
{
    "b",
    "w",
    "d",
    "q",
    NULL,
};

static const int sizes_count = sizeof ( sizes ) / sizeof ( sizes[0] ) - 1;

static int lookup ( const char* str, const char* const dict[] )
{
    int ret = 0;
    for ( ; dict[ret] != NULL; ret++ )
    {
        if ( !strcmp ( str, dict[ret] ) )
        {
            break;
        }
    }
    return ret;
}

memblock padseries[256];
memblock memseries[65536];
__thread void* thread_cand;

int maxseries = 0;

typedef void ( *handler_func ) ( int argc, const char* args[] );

static void malloc_hdl ( int argc, const char* args[] );
static void calloc_hdl ( int argc, const char* args[] );
static void realloc_hdl ( int argc, const char* args[] );
static void free_hdl ( int argc, const char* args[] );
static void fopen_hdl ( int argc, const char* args[] );
static void fclose_hdl ( int argc, const char* args[] );
static void dump_hdl ( int argc, const char* args[] );
static void write_hdl ( int argc, const char* args[] );
static void list_hdl ( int argc, const char* args[] );
static void leak_hdl ( int argc, const char* args[] );
static void minfo_hdl ( int argc, const char* args[] );
static void mmap_hdl ( int argc, const char* args[] );

static const handler_func handlers[] =
{
    malloc_hdl, // malloc <bytes> <index_to_store>
    calloc_hdl, // calloc <bytes> <index_to_store>
    realloc_hdl,// realloc <addr> <bytes> <index_to_store>
    free_hdl,   // free <addr>
    fopen_hdl,  // fopen <filename> <mode> <index_to_store>
    fclose_hdl, // fclose <addr>
    dump_hdl,   // dump <size_identifier> <addr> <elem_count>
    write_hdl,  // write <size_identifier> <addr> <val>
    list_hdl,   // list
    leak_hdl,   // leak
    minfo_hdl,  // minfo
    mmap_hdl,   // mmap
    NULL,
};

int main()
{
    setvbuf ( stdin, 0, 2, 0 );
    setvbuf ( stdout, 0, 2, 0 );
    setvbuf ( stderr, 0, 2, 0 );
    while ( true )
    {
        char buf[256];
        //eprintf ( "New loop!\n" );
        char* saveptr;
        if ( !fgets ( buf, 256, stdin ) )
        {
            break;
        }
        eprintf ( "%s", buf );
        char* toks[256];
        int tok_count = 0;
        for ( char* tok = strtok_r ( buf, " \n", &saveptr ); tok; tok = strtok_r ( NULL, " \n", &saveptr ) ) // note the usage of strtok
        {
            toks[tok_count++] = tok;
        }
        toks[tok_count] = NULL;
        if ( toks[0] != NULL )
        {
            int funci = lookup ( toks[0], cmds );
            if ( funci == cmd_count )
            {
                eprintf ( "Error: Unrecognized command: %s\n", toks[0] );
            }
            else
            {
                ( handlers[funci] ) ( tok_count, ( const char** ) toks );
            }
        }
    }
    return 0;
}

static bool assert_argc ( int argc, int planned_argc, const char* func_name )
{
    if ( argc < planned_argc )
    {
        eprintf ( "Error: Command %s needs %d arguments, %d given\n", func_name, planned_argc, argc );
        return false;
    }
    if ( argc > planned_argc )
    {
        eprintf ( "Warning: Command %s needs %d arguments, %d given\n", func_name, planned_argc, argc );
    }
    return true;
}

static bool strtol_wr ( const char* str, long& longint )
{
    errno = 0;
    char* endptr = NULL;
    long val = strtol ( str, &endptr, 0 );
    if ( ( errno == ERANGE && ( val == LONG_MAX || val == LONG_MIN ) )
            || ( errno != 0 && val == 0 ) )
    {
        eprintf ( "Error: The long integer was out of range. (ERANGE)\n" );
        return false;
    }
    if ( endptr == str )
    {
        eprintf ( "Error: No digits were found!\n" );
        return false;
    }
    // If we got here, strtol() successfully parsed a number
    if ( *endptr != '\0' )
    {
        eprintf ( "Warning: Further characters after number: %s\n", endptr );
    }
    longint = val;
    return true;
}

static void malloc_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 3, "malloc" ) )
    {
        return;
    }
    long arg1 = 0, arg2 = 0;
    if ( !strtol_wr ( args[1], arg1 ) || !strtol_wr ( args[2], arg2 ) )
    {
        eprintf ( "Error: invalid long int parameter on malloc!\n" );
        return;
    }
    if ( maxseries <= arg2 )
    {
        maxseries = arg2 + 1;
    }
    memseries[arg2] = {malloc ( arg1 ), arg1};
}

static void calloc_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 3, "calloc" ) )
    {
        return;
    }
    long arg1 = 0, arg2 = 0;
    if ( !strtol_wr ( args[1], arg1 ) || !strtol_wr ( args[2], arg2 ) )
    {
        eprintf ( "Error: invalid long int parameter on calloc!\n" );
        return;
    }
    if ( maxseries <= arg2 )
    {
        maxseries = arg2 + 1;
    }
    memseries[arg2] = {calloc ( arg1, 1 ), arg1};
}

static void realloc_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 4, "realloc" ) )
    {
        return;
    }
    long arg1 = 0, arg2 = 0, arg3 = 0;
    if ( !strtol_wr ( args[1], arg1 ) || !strtol_wr ( args[2], arg2 ) || !strtol_wr ( args[3], arg3 ) )
    {
        eprintf ( "Error: invalid long int parameter on realloc!\n" );
        return;
    }
    if ( maxseries <= arg3 )
    {
        maxseries = arg3 + 1;
    }
    memseries[arg3] = {realloc ( ( void* ) arg1, arg2 ), arg2};
}

static void free_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 2, "free" ) )
    {
        return;
    }
    long arg1 = 0;
    if ( !strtol_wr ( args[1], arg1 ) )
    {
        eprintf ( "Error: invalid long int parameter on free!\n" );
        return;
    }
    free ( ( void* ) arg1 );
}

static void fopen_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 4, "fopen" ) )
    {
        return;
    }
    long arg3 = 0;
    if ( !strtol_wr ( args[3], arg3 ) )
    {
        eprintf ( "Error: invalid long int parameter on fopen!\n" );
        return;
    }
    if ( maxseries <= arg3 )
    {
        maxseries = arg3 + 1;
    }
    memseries[arg3] = {fopen ( ( char* ) args[1], ( char* ) args[2] ), sizeof ( FILE ) };
}

static void fclose_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 2, "fclose" ) )
    {
        return;
    }
    long arg1 = 0;
    if ( !strtol_wr ( args[1], arg1 ) )
    {
        eprintf ( "Error: invalid long int parameter on fclose!\n" );
        return;
    }
    fclose ( ( FILE* ) arg1 );
}

static void dump_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 4, "dump" ) )
    {
        return;
    }
    long arg1 = 0, arg2 = 0, arg3 = 0;
    arg1 = lookup ( args[1], sizes );
    if ( arg1 == sizes_count )
    {
        eprintf ( "Error: invalid size identifier parameter on dump\n" );
        return;
    }
    if ( !strtol_wr ( args[2], arg2 ) || !strtol_wr ( args[3], arg3 ) )
    {
        eprintf ( "Error: invalid long int parameter on dump!\n" );
        return;
    }
    long single_element_size = 1 << arg1;
    for ( long i = 0; i < arg3; i++ )
    {
        switch ( arg1 )
        {
            case 0:
                printf ( "%02x ", * ( unsigned char* ) arg2 );
                break;
            case 1:
                printf ( "%04x ", * ( unsigned short* ) arg2 );
                break;
            case 2:
                printf ( "%08x ", * ( unsigned int* ) arg2 );
                break;
            case 3:
                printf ( "%016lx ", * ( unsigned long* ) arg2 );
                break;
            default:
                eprintf ( "Warning: This branch should not be evaluated! Check your code!\n" );
                break;
        }
        arg2 += single_element_size;
        if ( ( ( ( ( i + 1 ) & 0xff ) << arg1 ) & 0x0f ) == 0 )
        {
            printf ( "\n" );
        }
    }
    printf ( "\n====\n" );
    fflush ( stdout );
}

static void write_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 4, "write" ) )
    {
        return;
    }
    long arg1 = 0, arg2 = 0, arg3 = 0;
    arg1 = lookup ( args[1], sizes );
    if ( arg1 == sizes_count )
    {
        eprintf ( "Error: invalid size identifier parameter on write\n" );
        return;
    }
    if ( !strtol_wr ( args[2], arg2 ) || !strtol_wr ( args[3], arg3 ) )
    {
        eprintf ( "Error: invalid long int parameter on write!\n" );
        return;
    }
    switch ( arg1 )
    {
        case 0:
            * ( unsigned char* ) arg2 = arg3;
            break;
        case 1:
            * ( unsigned short* ) arg2 = arg3;
            break;
        case 2:
            * ( unsigned int* ) arg2 = arg3;
            break;
        case 3:
            * ( unsigned long* ) arg2 = arg3;
            break;
        default:
            eprintf ( "Warning: This branch should not be evaluated! Check your code!\n" );
            break;
    }
}

static void list_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 1, "list" ) )
    {
        return;
    }
    ( void ) args;
    for ( int i = 0; i < maxseries; i++ )
    {
        printf ( "%d %016lx %lx\n", i, ( unsigned long ) memseries[i].first, memseries[i].second );
    }
    printf ( "====\n" );
    fflush ( stdout );
}

//extern unsigned long __malloc_hook;

static void leak_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 1, "leak" ) )
    {
        return;
    }
    ( void ) args;
    {
        printf ( "%016lx %s\n", ( unsigned long ) &main, ":text<main>" );
        printf ( "%016lx %s\n", ( unsigned long ) &memseries, ":data<memseries>" );
        printf ( "%016lx %s\n", ( unsigned long ) &thread_cand, ":tls<&thread_cand>" );
        printf ( "%016lx %s\n", ( unsigned long ) * ( ( ( long* ) ( &thread_cand ) ) + 6 ), ":tls<canary>" );
        printf ( "%016lx %s\n", ( unsigned long ) stdin, ":libc<stdin>" );
        printf ( "%016lx %s\n", ( unsigned long ) &__malloc_hook, ":libc<__malloc_hook>" );
        printf ( "%016lx %s\n", ( unsigned long ) &errno, ":libc<errno>" );
        printf ( "%016lx %s\n", ( unsigned long ) &args, ":stack<args>" );
    }
    printf ( "====\n" );
    fflush ( stdout );
}

static void minfo_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 1, "minfo" ) )
    {
        return;
    }
    ( void ) args;
    malloc_info ( 0, stdout );
    printf ( "====\n" );
    fflush ( stdout );
}

static void mmap_hdl ( int argc, const char* args[] )
{
    if ( !assert_argc ( argc, 7, "write" ) )
    {
        return;
    }
    long argl[6];
    long ret = 0;
    for ( int i = 0; i < 6; i++ )
    {
        if ( !strtol_wr ( args[i+1], argl[i] ) )
        {
            eprintf ( "Error: invalid long int parameter on mmap_hdl!\n" );
            ret = -1L;
            goto OUTPUT;
        }
    }
    ret = ( long ) mmap ( ( void* ) argl[0], argl[1], argl[2], argl[3], argl[4], argl[5] );
OUTPUT:
    printf ( "mmap return: %#016lx\n", ret );
    if ( ret == -1 )
    {
        perror ( "mmap" );
    }
    fflush ( stdout );
    fflush ( stderr );
}

