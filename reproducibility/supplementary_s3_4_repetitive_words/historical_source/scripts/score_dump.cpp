#include "common.hpp"
#include <iomanip>
int main(int argc,char**argv){try{if(argc!=4)throw std::runtime_error("usage: score_dump k config_dir comma_separated_methods < encoded_values.txt");int k=std::stoi(argv[1]);fixed_config_dir=argv[2];auto methods=strings(argv[3]);std::vector<U>xs;U x;while(std::cin>>x){if(k<32&&x>kmask(k))throw std::runtime_error("out of range");xs.push_back(x);}std::cout<<"method,input,score\n";for(auto&m:methods){Hasher h(m,k,42);for(auto y:xs)std::cout<<m<<','<<y<<','<<h(y)<<'\n';}return 0;}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
