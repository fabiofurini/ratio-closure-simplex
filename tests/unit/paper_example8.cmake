execute_process(
  COMMAND "${PROGRAM}" solve --instance "${INSTANCE}"
  RESULT_VARIABLE status
  OUTPUT_VARIABLE output
  ERROR_VARIABLE errors)
if(NOT status EQUAL 0)
  message(FATAL_ERROR "pclp failed (${status}): ${errors}")
endif()
string(JSON solver_status GET "${output}" status)
string(JSON objective GET "${output}" objective)
if(NOT solver_status STREQUAL "optimal")
  message(FATAL_ERROR "unexpected status: ${solver_status}")
endif()
if(NOT objective STREQUAL "7.0")
  message(FATAL_ERROR "expected objective 7.0, got ${objective}")
endif()
