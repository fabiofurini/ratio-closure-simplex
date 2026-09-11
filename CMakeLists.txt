cmake_minimum_required(VERSION 3.25)

project(precedence_lp VERSION 0.1.0 LANGUAGES CXX)

option(PCLP_ENABLE_SANITIZERS "Enable address and undefined-behaviour sanitizers" OFF)
option(PCLP_LTO "Enable interprocedural optimization" OFF)
option(PCLP_NATIVE "Build for the current CPU" OFF)
option(PCLP_DISABLE_LEAK_CHECK "Disable LSan in traced environments" OFF)
option(PCLP_TEST_HIGHS "Require SciPy/HiGHS differential acceptance tests" OFF)

file(GLOB_RECURSE PCLP_SOURCE_FILES CONFIGURE_DEPENDS src/*.cpp include/*.hpp tests/*.py tests/*.cpp)
list(APPEND PCLP_SOURCE_FILES "${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt" "${CMAKE_CURRENT_SOURCE_DIR}/third_party/nlohmann/json.hpp" "${CMAKE_CURRENT_SOURCE_DIR}/include/pclp/build_info.hpp.in")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS ${PCLP_SOURCE_FILES})
set(PCLP_HASH_INPUT "")
foreach(source IN LISTS PCLP_SOURCE_FILES)
  file(SHA256 "${source}" source_hash)
  string(APPEND PCLP_HASH_INPUT "${source_hash}")
endforeach()
string(SHA256 PCLP_SOURCE_HASH "${PCLP_HASH_INPUT}")
string(TOUPPER "${CMAKE_BUILD_TYPE}" PCLP_TYPE)
set(PCLP_BUILD_FLAGS "${CMAKE_CXX_FLAGS} ${CMAKE_CXX_FLAGS_${PCLP_TYPE}};sanitizers=${PCLP_ENABLE_SANITIZERS};LTO=${PCLP_LTO};native=${PCLP_NATIVE}")
configure_file(include/pclp/build_info.hpp.in generated/pclp/build_info.hpp @ONLY)

add_library(pclp STATIC src/ratio_closure.cpp src/basis_forest.cpp src/graph.cpp src/engine.cpp src/certificates.cpp src/flow.cpp src/backends.cpp)
target_include_directories(pclp
  PUBLIC include
  PRIVATE third_party)
target_compile_features(pclp PUBLIC cxx_std_20)
target_compile_options(pclp PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow)

if(PCLP_ENABLE_SANITIZERS)
  target_compile_options(pclp PUBLIC -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(pclp PUBLIC -fsanitize=address,undefined)
endif()
if(PCLP_LTO)
  include(CheckIPOSupported)
  check_ipo_supported(RESULT PCLP_IPO_OK OUTPUT PCLP_IPO_ERROR)
  if(NOT PCLP_IPO_OK)
    message(FATAL_ERROR "${PCLP_IPO_ERROR}")
  endif()
  set_property(TARGET pclp PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
endif()
if(PCLP_NATIVE)
  target_compile_options(pclp PRIVATE -march=native)
endif()

add_executable(pclp_cli src/main.cpp src/io.cpp)
set_target_properties(pclp_cli PROPERTIES OUTPUT_NAME pclp)
target_link_libraries(pclp_cli PRIVATE pclp)
target_include_directories(pclp_cli PRIVATE third_party "${CMAKE_CURRENT_BINARY_DIR}/generated")
if(PCLP_LTO)
  set_property(TARGET pclp_cli PROPERTY INTERPROCEDURAL_OPTIMIZATION TRUE)
endif()
if(PCLP_ENABLE_SANITIZERS)
  target_compile_options(pclp_cli PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(pclp_cli PRIVATE -fsanitize=address,undefined)
endif()

option(PCLP_BUILD_LEGACY "Build the 2023 Forest Simplex prototype as a measured baseline" ON)
if(PCLP_BUILD_LEGACY AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/legacy/forest2023/src/Forest.cpp")
  # The prototype is compiled as it was written: its warnings are part of the
  # historical record and are not fixed here.
  add_executable(pclp_legacy legacy/forest2023/legacy_main.cpp
    legacy/forest2023/src/Forest.cpp legacy/forest2023/src/Graph_v4.cpp)
  set_target_properties(pclp_legacy PROPERTIES OUTPUT_NAME pclp_legacy)
  target_include_directories(pclp_legacy PRIVATE legacy/forest2023 third_party)
  # The prototype predates C++20 stream rules; it is compiled at the standard it
  # was written for rather than being edited to satisfy a newer one.
  set_target_properties(pclp_legacy PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
  target_compile_options(pclp_legacy PRIVATE -w)
endif()

# The 2024 prototype is the later state of the same code: it walks the whole
# macroitem sequence instead of stopping at one oracle.  Both are kept, and both
# are measured.  Unlike the 2023 one it needs LEMON, because the historical
# instance struct gained a ListGraph member; the vendored copy in third_party is
# header-only for everything this path touches.
if(PCLP_BUILD_LEGACY AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/legacy/forest2024/src/Forest.cpp"
                     AND EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/lemon/include/lemon/config.h")
  add_executable(pclp_legacy2024 legacy/forest2024/legacy_main.cpp
    legacy/forest2024/src/Forest.cpp legacy/forest2024/src/Graph_v4.cpp)
  set_target_properties(pclp_legacy2024 PROPERTIES OUTPUT_NAME pclp_legacy2024)
  target_include_directories(pclp_legacy2024 PRIVATE legacy/forest2024 third_party
    third_party/lemon/include)
  target_link_libraries(pclp_legacy2024 PRIVATE
    "${CMAKE_CURRENT_SOURCE_DIR}/third_party/lemon/lib/libemon.a")
  set_target_properties(pclp_legacy2024 PROPERTIES CXX_STANDARD 17 CXX_STANDARD_REQUIRED ON)
  target_compile_options(pclp_legacy2024 PRIVATE -w)
endif()

include(CTest)
if(BUILD_TESTING)
find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(
  NAME paper_example8
  COMMAND ${CMAKE_COMMAND} -DPROGRAM=$<TARGET_FILE:pclp_cli>
          -DINSTANCE=${CMAKE_CURRENT_SOURCE_DIR}/tests/fixtures/paper_example8.json
          -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/unit/paper_example8.cmake)
add_test(
  NAME random_differential
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/unit/random_differential.py
          $<TARGET_FILE:pclp_cli>)
add_executable(basis_forest_test tests/unit/basis_forest.cpp)
target_link_libraries(basis_forest_test PRIVATE pclp)
if(PCLP_ENABLE_SANITIZERS)
  target_compile_options(basis_forest_test PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_options(basis_forest_test PRIVATE -fsanitize=address,undefined)
endif()
add_test(NAME basis_forest COMMAND basis_forest_test)
add_executable(engine_test tests/unit/engine.cpp)
target_link_libraries(engine_test PRIVATE pclp)
add_test(NAME engine_invariants COMMAND engine_test)
set(PCLP_ACCEPTANCE_FLAGS --report ${CMAKE_CURRENT_BINARY_DIR}/acceptance.json)
if(PCLP_TEST_HIGHS)
  execute_process(COMMAND ${Python3_EXECUTABLE} -c "import scipy.optimize" RESULT_VARIABLE PCLP_SCIPY_STATUS)
  if(NOT PCLP_SCIPY_STATUS EQUAL 0)
    message(FATAL_ERROR "PCLP_TEST_HIGHS requires SciPy in Python3_EXECUTABLE")
  endif()
  list(APPEND PCLP_ACCEPTANCE_FLAGS --highs)
endif()
add_test(NAME solver_acceptance COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tests/solver_suite.py
  $<TARGET_FILE:pclp_cli> ${PCLP_ACCEPTANCE_FLAGS})
set_tests_properties(solver_acceptance PROPERTIES TIMEOUT 180)

if(PCLP_ENABLE_SANITIZERS AND PCLP_DISABLE_LEAK_CHECK)
  set_tests_properties(paper_example8 random_differential basis_forest engine_invariants solver_acceptance PROPERTIES
    ENVIRONMENT "ASAN_OPTIONS=detect_leaks=0")
endif()
endif()
