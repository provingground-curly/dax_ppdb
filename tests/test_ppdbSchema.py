# This file is part of dax_ppdb.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Unit test for PpdbSchema class.
"""

import os
import unittest

import lsst.afw.table as afwTable
from lsst.dax.ppdb import PpdbSchema, make_minimal_dia_object_schema, make_minimal_dia_source_schema
from lsst.utils import getPackageDir
import lsst.utils.tests
from sqlalchemy import create_engine


def _make_case_conficting_dia_object_schema():
    """Make schema which has column name with case mismatch.

    Copy of make_minimal_dia_object_schema with additional column.
    """
    schema = afwTable.SourceTable.makeMinimalSchema()
    schema.addField("pixelId", type='L',
                    doc='Unique spherical pixelization identifier.')
    schema.addField("nDiaSources", type='L')
    # baseline schema has column `radecTai`
    schema.addField("RaDecTai", type='D')
    return schema


def _data_file_name(basename):
    """Return path name of a data file.
    """
    return os.path.join(getPackageDir("dax_ppdb"), "data", basename)


class PpdbSchemaTestCase(unittest.TestCase):
    """A test case for PpdbSchema class
    """

    @classmethod
    def setUpClass(cls):
        pass

    def _assertTable(self, table, name, ncol):
        """validation for tables schema.

        Parameters
        ----------
        table : `sqlalchemy.Table`
        name : `str`
            Expected table name
        ncol : `int`
            Expected number of columns
        """
        self.assertIsNotNone(table)
        self.assertEqual(table.name, name)
        self.assertEqual(len(table.columns), ncol)

    def test_makeSchema(self):
        """Test for creating schemas.

        Schema is defined in YAML files, some checks here depend on that
        configuration and will need to be updated when configuration changes.
        """
        engine = create_engine('sqlite://')

        # create standard (baseline) schema
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"))
        schema.makeSchema()
        self._assertTable(schema.objects, "DiaObject", 92)
        self.assertEqual(len(schema.objects.primary_key), 2)
        self.assertIsNone(schema.objects_nightly)
        self.assertIsNone(schema.objects_last)
        self._assertTable(schema.sources, "DiaSource", 108)
        self._assertTable(schema.forcedSources, "DiaForcedSource", 7)

        # create schema using prefix
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            prefix="Pfx")
        # Drop existing tables (but we don't check it here)
        schema.makeSchema(drop=True)
        self._assertTable(schema.objects, "PfxDiaObject", 92)
        self.assertIsNone(schema.objects_nightly)
        self.assertIsNone(schema.objects_last)
        self._assertTable(schema.sources, "PfxDiaSource", 108)
        self._assertTable(schema.forcedSources, "PfxDiaForcedSource", 7)

        # use different indexing for DiaObject, need extra schema for that
        schema = PpdbSchema(engine=engine,
                            dia_object_index="pix_id_iov",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            extra_schema_file=_data_file_name("ppdb-schema-extra.yaml"))
        schema.makeSchema(drop=True)
        self._assertTable(schema.objects, "DiaObject", 94)
        self.assertEqual(len(schema.objects.primary_key), 3)
        self.assertIsNone(schema.objects_nightly)
        self.assertIsNone(schema.objects_last)
        self._assertTable(schema.sources, "DiaSource", 108)
        self._assertTable(schema.forcedSources, "DiaForcedSource", 7)

        # use DiaObjectLast table for DiaObject, need extra schema for that
        schema = PpdbSchema(engine=engine,
                            dia_object_index="last_object_table",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            extra_schema_file=_data_file_name("ppdb-schema-extra.yaml"))
        schema.makeSchema(drop=True)
        self._assertTable(schema.objects, "DiaObject", 94)
        self.assertEqual(len(schema.objects.primary_key), 2)
        self.assertIsNone(schema.objects_nightly)
        self._assertTable(schema.objects_last, "DiaObjectLast", 18)
        self.assertEqual(len(schema.objects_last.primary_key), 2)
        self._assertTable(schema.sources, "DiaSource", 108)
        self._assertTable(schema.forcedSources, "DiaForcedSource", 7)

        # baseline schema with nightly DiaObject
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=True,
                            schema_file=_data_file_name("ppdb-schema.yaml"))
        schema.makeSchema(drop=True)
        self._assertTable(schema.objects, "DiaObject", 92)
        self._assertTable(schema.objects_nightly, "DiaObjectNightly", 92)
        self.assertIsNone(schema.objects_last)
        self._assertTable(schema.sources, "DiaSource", 108)
        self._assertTable(schema.forcedSources, "DiaForcedSource", 7)

    def test_afwSchemaCaseSensitivity(self):
        """Test for column case mismatch errors.

        This is a specific test for when afw schema column names differ from
        PPDB schem in case only which should generate exception.

        Like all other tests this depends on the column naming in
        ppdb-schema.yaml.
        """
        engine = create_engine('sqlite://')

        afw_schemas = dict(DiaObject=_make_case_conficting_dia_object_schema(),
                           DiaSource=make_minimal_dia_source_schema())
        # column case mismatch should cause exception in constructor
        with self.assertRaises(ValueError):
            PpdbSchema(engine=engine,
                       dia_object_index="baseline",
                       dia_object_nightly=False,
                       schema_file=_data_file_name("ppdb-schema.yaml"),
                       column_map=_data_file_name("ppdb-afw-map.yaml"),
                       afw_schemas=afw_schemas)

    def test_getAfwSchema(self):
        """Test for getAfwSchema method.

        Schema is defined in YAML files, some checks here depend on that
        configuration and will need to be updated when configuration changes.
        """
        engine = create_engine('sqlite://')

        # create standard (baseline) schema, but use afw column map
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            column_map=_data_file_name("ppdb-afw-map.yaml"))
        schema.makeSchema()

        afw_schema, col_map = schema.getAfwSchema("DiaObject")
        self.assertEqual(len(col_map), 92)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # no BLOBs in afwTable, so count is lower
        self.assertEqual(afw_schema.getFieldCount(), 81)

        afw_schema, col_map = schema.getAfwSchema("DiaSource")
        self.assertEqual(len(col_map), 108)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        self.assertEqual(afw_schema.getFieldCount(), 108)

        afw_schema, col_map = schema.getAfwSchema("DiaForcedSource")
        self.assertEqual(len(col_map), 7)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # afw table adds 4 columns compared to out standard schema
        self.assertEqual(afw_schema.getFieldCount(), 7+4)

        # subset of columns
        afw_schema, col_map = schema.getAfwSchema("DiaObject",
                                                  ["diaObjectId", "ra", "decl", "ra_decl_Cov"])
        self.assertEqual(len(col_map), 4)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # one extra column exists for some reason for DiaObect in afw schema
        self.assertEqual(afw_schema.getFieldCount(), 5)

    def test_getAfwSchemaWithExtras(self):
        """Test for getAfwSchema method using extra afw schemas.

        Same as above but use non-default afw schemas, this adds few extra
        columns to the table schema
        """
        engine = create_engine('sqlite://')

        # create standard (baseline) schema, but use afw column map
        afw_schemas = dict(DiaObject=make_minimal_dia_object_schema(),
                           DiaSource=make_minimal_dia_source_schema())
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            column_map=_data_file_name("ppdb-afw-map.yaml"),
                            afw_schemas=afw_schemas)
        schema.makeSchema()

        afw_schema, col_map = schema.getAfwSchema("DiaObject")
        self.assertEqual(len(col_map), 94)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # no BLOBs in afwTable, so count is lower
        self.assertEqual(afw_schema.getFieldCount(), 82)

        afw_schema, col_map = schema.getAfwSchema("DiaSource")
        self.assertEqual(len(col_map), 108)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        self.assertEqual(afw_schema.getFieldCount(), 108)

        afw_schema, col_map = schema.getAfwSchema("DiaForcedSource")
        self.assertEqual(len(col_map), 7)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # afw table adds 4 columns compared to out standard schema
        self.assertEqual(afw_schema.getFieldCount(), 7+4)

        # subset of columns
        afw_schema, col_map = schema.getAfwSchema("DiaObject",
                                                  ["diaObjectId", "ra", "decl", "ra_decl_Cov"])
        self.assertEqual(len(col_map), 4)
        self.assertIsInstance(afw_schema, afwTable.Schema)
        # one extra column exists for some reason for DiaObect in afw schema
        self.assertEqual(afw_schema.getFieldCount(), 5)

    def test_getAfwColumns(self):
        """Test for getAfwColumns method.

        Schema is defined in YAML files, some checks here depend on that
        configuration and will need to be updated when configuration changes.
        """
        engine = create_engine('sqlite://')

        # create standard (baseline) schema, but use afw column map
        schema = PpdbSchema(engine=engine,
                            dia_object_index="baseline",
                            dia_object_nightly=False,
                            schema_file=_data_file_name("ppdb-schema.yaml"),
                            column_map=_data_file_name("ppdb-afw-map.yaml"))
        schema.makeSchema()

        col_map = schema.getAfwColumns("DiaObject")
        self.assertEqual(len(col_map), 92)
        # check few afw-specific names
        self.assertIn("id", col_map)
        self.assertIn("coord_ra", col_map)
        self.assertIn("coord_dec", col_map)

        col_map = schema.getAfwColumns("DiaSource")
        self.assertEqual(len(col_map), 108)
        # check few afw-specific names
        self.assertIn("id", col_map)
        self.assertIn("coord_ra", col_map)
        self.assertIn("coord_dec", col_map)


class MyMemoryTestCase(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
