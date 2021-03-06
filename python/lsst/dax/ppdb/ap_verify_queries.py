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

"""Contains convenience functions for accessing data from the Ppdb for use in
ApVerify.
"""

__all__ = ["countUnassociatedObjects", "isVisitProcessed"]

from sqlalchemy import (func, sql)


def countUnassociatedObjects(ppdb):
    """Return the number of DiaObjects that have only one DiaSource associated
    with them.

    Parameters
    ----------
    ppdb : `lsst.dax.ppdb.Ppdb`
        Ppdb object connected to an instantiated database.

    Returns
    -------
    count : `int`
        Number of DiaObjects with exactly one associated DiaSource.
    """
    # Retrieve the DiaObject table.
    table = ppdb._schema.objects

    # Construct the sql statement.
    stmt = sql.select([func.count()]).select_from(table).where(table.c.nDiaSources == 1)
    stmt = stmt.where(table.c.validityEnd == None)  # noqa: E711

    # Return the count.
    count = ppdb._engine.scalar(stmt)

    return count


def isVisitProcessed(ppdb, visitInfo):
    """Test whether data from an image has been loaded into the database.

    Parameters
    ----------
    ppdb : `lsst.dax.ppdb.Ppdb`
        Ppdb object connected to an instantiated database.
    visitInfo : `lsst.afw.image.VisitInfo`
        The metadata for the image of interest.

    Returns
    -------
    isProcessed : `bool`
        `True` if the data are present, `False` otherwise.
    """
    id = visitInfo.getExposureId()
    table = ppdb._schema.sources
    idField = table.c.ccdVisitId

    # Hopefully faster than SELECT DISTINCT
    query = sql.select([idField]).select_from(table) \
        .where(idField == id).limit(1)

    return ppdb._engine.scalar(query) is not None
