slick_version = "3.2.0-RC1"
slick_base = scala_jar("com.typesafe.slick", "slick", slick_version)
def slick(which):
  return scala_jar("com.typesafe.slick", "slick-" + which, slick_version)

slick_pg_version = '0.15.0-M3'
def slick_pg(which = None):
  return scala_jar('com.github.tminglei', 'slick-pg_' + which if which else 'slick-pg', slick_pg_version)

jar_library(
  name="slick",
  jars=[slick_base]
)

jar_library(
  name="slick-pg",
  jars=[slick_pg()]
)
jar_library(
  name="slick-pg-circe",
  jars=[slick_pg("circe-json")]
)

jar_library(
  name="slick-codegen",
  jars=[slick("codegen")]
)

jar_library(
  name="slick-hikaricp",
  jars=[slick("hikaricp")]
)

jar_library(
  name="scopt",
  jars=[scala_jar('com.github.scopt', 'scopt', '3.5.0')]
)
