import {dsvFormat} from "d3-dsv";
import {extractLegadoRows, FIELDS} from "../../../scripts/legado/legado-extract.mjs";

process.stdout.write(dsvFormat(";").format(extractLegadoRows(), FIELDS));
