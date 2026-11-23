// Independent compatibility loader for the historical native binary format.
// This is not the original GreedyMini loader. See the adjacent README.
#include <cstdio>
#include <memory>

static std::vector<uint64_t> load_vector_from_file(const std::string& path) {
    using File = std::unique_ptr<std::FILE, decltype(&std::fclose)>;
    File input(std::fopen(path.c_str(), "rb"), &std::fclose);
    if (!input) {
        std::cerr << "Unable to open file for reading: " << path << std::endl;
        return {};
    }
    size_t count = 0;
    if (std::fread(&count, 1, sizeof(count), input.get()) != sizeof(count))
        return {};
    std::vector<uint64_t> values(count);
    if (!values.empty())
        (void)std::fread(values.data(), 1, values.size() * sizeof(uint64_t), input.get());
    return values;
}
