include_guard()
cmake_minimum_required(VERSION 3.18...3.27 FATAL_ERROR)

include(art::tool)
include(BasicPlugin)

# Generate a CMake plugin builder macro for tools of type lar::HitReaderTool for
# automatic invocation by build_plugin().
macro(lar::HitReaderTool NAME)
  cet_build_plugin(${NAME} art::tool ${ARGN} LIBRARIES;CONDITIONAL;larreco::HitReaderTool)
endmacro()
