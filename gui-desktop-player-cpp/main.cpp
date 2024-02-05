#include "player.h"

int main(int argc, char * argv[])
{
    std::string p(argv[0]);
    size_t last = p.find_last_of("/\\");
    if(last != std::string::npos) {player::working_directory = p.substr(0, last);}
    player::load_config();
    curl_global_init(CURL_GLOBAL_DEFAULT);
    player::backend();
    curl_global_cleanup();
    return 0;
}
