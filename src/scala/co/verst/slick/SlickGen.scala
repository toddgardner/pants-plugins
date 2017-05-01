package co.verst.slick

import scala.concurrent.Await
import scala.concurrent.duration.Duration
import slick.jdbc.JdbcBackend.Database
import slick.{model => m}
import com.github.tminglei.slickpg._
import com.typesafe.config.ConfigFactory
import java.io.File
import scala.concurrent.ExecutionContext.Implicits.global
import slick.jdbc.meta.MTable

import slick.sql.SqlProfile

trait VerstPostgresProfile extends ExPostgresProfile with PgCirceJsonSupport {
  override val pgjson = "jsonb"

  override val api = new API with JsonImplicits
}

object VerstPostgresProfile extends VerstPostgresProfile

//
// options logic taken from:
// https://github.com/slick/slick/blob/3.1.1/slick-codegen/src/main/scala/slick/codegen/AbstractGenerator.scala#L231-L234
//

case class SlickGenArgs(configEntry: String = "",
                        configFile: File = new File("doesnotexist"),
                        outputDir: String = "",
                        driverClass: String =
                          "com.github.tminglei.slickpg.ExPostgresProfile",
                        generatedPackage: String = "slick.gen",
                        enclosingObject: String = "Tables",
                        fileName: String = "Tables.scala",
                        excludedTables: Set[String] = Set(),
                        schema: Option[String] = None)

object SlickGen extends App {

  val JSON_LENGTH = 65535

  def generateTables(args: SlickGenArgs): Unit = {
    val SlickGenArgs(configEntry,
                     configFile,
                     outputDir,
                     driverClass,
                     generatedPackage,
                     enclosingObject,
                     fileName,
                     excludeTables,
                     schema) = args
    val tables = VerstPostgresProfile.defaultTables.map(tables =>
          tables.filterNot { x: MTable =>
        excludeTables.contains(x.name.name)
      }.filter { x: MTable =>
        schema.isEmpty || schema == x.name.schema
      }.toSeq)
    val modelAction = VerstPostgresProfile.createModel(Some(tables))
    val config = ConfigFactory.parseFile(configFile).resolve
    val db = Database.forConfig(configEntry, config)

    try {

      Await.result(db.run(modelAction).map { model =>
        val codeGen = new WideTableGenerator(model) {
          val Length = slick.relational.RelationalProfile.ColumnOption.Length

          override def packageCode(profile: String,
                                   pkg: String,
                                   container: String,
                                   parentType: Option[String]): String = {
            // TFH: Adding the import of VerstPostgresProfile.api._ after the pkg
            val pkgAndImport =
              s"$pkg\nimport co.verst.slick.VerstPostgresProfile.api._\n"
            s"// scalastyle:off\n${super.packageCode(profile, pkgAndImport, container, parentType)}\n// scalastyle:on"
          }
        }.writeToFile(driverClass,
                      outputDir,
                      generatedPackage,
                      enclosingObject,
                      fileName)
      }, Duration.Inf)
    } finally {
      db.shutdown
    }
  }

  private[this] val parser = new scopt.OptionParser[SlickGenArgs]("") {
    opt[String]("config-entry") action { (entry, cfg) =>
      cfg.copy(configEntry = entry)
    }
    opt[File]("config-file") action { (file, cfg) =>
      cfg.copy(configFile = file)
    }
    opt[String]("output-dir") action { (dir, cfg) =>
      cfg.copy(outputDir = dir)
    }
    opt[String]("driver") action { (driver, cfg) =>
      cfg.copy(driverClass = driver)
    }
    opt[String]("package") action { (pkg, cfg) =>
      cfg.copy(generatedPackage = pkg)
    }
    opt[Seq[String]]("exclude-tables") action { (tables, cfg) =>
      cfg.copy(excludedTables = tables.toSet)
    }
    opt[String]("schema") action { (schema, cfg) =>
      cfg.copy(schema = Some(schema))
    }
  }

  parser
    .parse(args, SlickGenArgs())
    .fold {
      sys.exit(1)
    } { config =>
      generateTables(config)
    }

}
