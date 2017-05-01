package co.verst.slick

import slick.codegen.SourceCodeGenerator
import slick.{model => m}

// scalastyle:off methodname
class WideTableGenerator(model: m.Model) extends SourceCodeGenerator(model) {
  override def Table = { table: m.Table =>
    if (table.columns.size > 22) {
      new super.Table(table) with WideTableDef
    } else {
      new super.Table(table) with RegularTableDef
    }
  }

  trait RegularTableDef { self: super.TableDef =>

    override def EntityType = new EntityType {
      override def caseClassFinal = false
    }
  }

  trait WideTableDef { self: super.TableDef =>
    override def hlistEnabled = false

    override def extractor =
      throw new RuntimeException(
          "No extractor is defined for a table with more than 22 columns")

    def compoundRepName = s"${tableName(model.name.table)}Rep"
    def compoundLiftedValue(values: Seq[String]): String = {
      s"""${compoundRepName}(${values.mkString(",")})"""
    }

    override def TableClass = new WideTableClassDef
    class WideTableClassDef extends TableClassDef {
      def repConstructor = compoundLiftedValue(columns.map(_.name))
      override def star = {
        s"def * = ${repConstructor}"
      }
      override def option = {
        s"def ? = Rep.Some(${repConstructor})"
      }
    }

    override def definitions = Seq[Def](
        EntityType,
        CompoundRep,
        RowShape,
        PlainSqlMapper,
        TableClass,
        TableValue
    )

    override def compoundValue(values: Seq[String]) =
      s"""${entityName(model.name.table)}(${values.mkString(", ")})"""

    override def factory = ""

    def CompoundRep = new CompoundRepDef
    class CompoundRepDef extends TypeDef {
      override def code: String = {
        val args = columns
          .map(
              c =>
                c.default
                  .map(v => s"${c.name}: Rep[${c.exposedType}] = $v")
                  .getOrElse(
                      s"${c.name}: Rep[${c.exposedType}]"
                ))
          .mkString(", ")

        val prns = (parents.take(1).map(" extends " + _) ++
              parents.drop(1).map(" with " + _)).mkString("")

        s"""case class $name($args)$prns"""
      }
      override def doc: String = "" // TODO
      override def rawName: String = compoundRepName
    }

    def RowShape = new RowShapeDef
    class RowShapeDef extends TypeDef {
      override def code: String = {
        val shapes = (columns.map { column =>
          val repType = s"Rep[${column.exposedType}]"
          s"implicitly[Shape[FlatShapeLevel, ${repType}, ${column.exposedType}, ${repType}]]"
        }).mkString(", ")
        val shapesSeq = s"Seq(${shapes})"
        def seqConversionCode(columnTypeMapper: String => String) =
          columns.zipWithIndex.map {
            case (column, index) =>
              s"seq(${index}).asInstanceOf[${columnTypeMapper(column.exposedType)}]"
          }

        val seqParseFunctionBody = seqConversionCode(identity)
        val liftedSeqParseBody = seqConversionCode { tpe =>
          s"Rep[${tpe}]"
        }
        val seqParseFunction = s"seq => ${compoundValue(seqParseFunctionBody)}"
        val liftedSeqParseFunc =
          s"seq => ${compoundLiftedValue(liftedSeqParseBody)}"

        s"""implicit object ${name} extends ProductClassShape(${shapesSeq}, ${liftedSeqParseFunc}, ${seqParseFunction})"""

      }
      override def doc: String = "" // TODO
      override def rawName: String = s"${tableName(model.name.table)}Shape"
    }

    class WideIndexDef(index: m.Index) extends self.Index(index) {
      override def code = {
        val unique = if (model.unique) s", unique=true" else ""
        s"""val $name = index("$dbName", ${tuppleValue(columns.map(_.name))}$unique)"""
      }
    }

    override def Index = new WideIndexDef(_)

    def tuppleValue(values: Seq[String]): String = {
      if (values.size == 1) { values.head } else if (values.size <= 22) {
        s"""(${values.mkString(", ")})"""
      } else { throw new Exception("Cannot generate tuple for > 22 columns.") }
    }

  }
}
// scalastyle:on methodname
