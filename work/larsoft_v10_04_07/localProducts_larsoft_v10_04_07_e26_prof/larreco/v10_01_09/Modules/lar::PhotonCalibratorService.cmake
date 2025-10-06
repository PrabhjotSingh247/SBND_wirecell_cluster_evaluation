include_guard()
cmake_minimum_required(VERSION 3.18...3.27 FATAL_ERROR)

include(art::service)
include(BasicPlugin)

# Generate a CMake plugin builder macro for tools of type lar::PhotonCalibratorService for
# automatic invocation by build_plugin().
macro(lar::PhotonCalibratorService NAME)
  cet_build_plugin(${NAME} art::service ${ARGN} LIBRARIES;CONDITIONAL;larreco::PhotonCalibratorService)
endmacro()
