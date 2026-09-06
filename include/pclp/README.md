# Interfacce

core.hpp espone istanze, opzioni, risultati, query e verificatori.
engine.hpp, graph.hpp e basis_forest.hpp implementano il workspace interno.
io.hpp è utilizzato dalla CLI con nlohmann/json; build_info.hpp è generato da
CMake a partire dal template .in e rimane nella directory di build.
