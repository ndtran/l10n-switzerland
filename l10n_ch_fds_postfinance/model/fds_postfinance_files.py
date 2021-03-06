# -*- coding: utf-8 -*-
##############################################################################
#
#    Swiss Postfinance File Delivery Services module for Odoo
#    Copyright (C) 2014 Compassion CH
#    @author: Nicolas Tran
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, exceptions
import logging

_logger = logging.getLogger(__name__)


class fds_postfinance_files(models.Model):
    ''' Model of the informations and files downloaded on FDS PostFinance
        (Keep files in the database)
    '''
    _name = 'fds.postfinance.files'

    fds_account_id = fields.Many2one(
        comodel_name='fds.postfinance.account',
        string='FDS account id',
        ondelete='restrict',
        readonly=True,
        help='file related to FDS account id'
    )
    files = fields.Binary(
        string='Files',
        readonly=True,
        help='the downloaded file'
    )
    bankStatment_id = fields.Many2one(
        comodel_name='account.bank.statement',
        string='Bank Statment id',
        ondelete='restrict',
        readonly=True,
        help='the generate bank statment id'
    )
    filename = fields.Char(
        string='Filename',
        readonly=True,
        help='The name of the file'
    )
    directory_id = fields.Many2one(
        'fds.postfinance.files.directory',
        string='Directory',
        ondelete='restrict',
        readonly=True,
        help='location directory of the file'
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        related='directory_id.journal_id',
        string='journal',
        ondelete='restrict',
        readonly=True,
        help='default journal for this file'
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'),
                   ('finish', 'Finish'),
                   ('error', 'Error')],
        readonly=True,
        default='draft',
        help='state of file'
    )

    ##################################
    #         Button action          #
    ##################################
    @api.multi
    def import_button(self):
        ''' convert the file to record of model bankStatment.
            Called by pressing import button.

            :return None:
        '''
        self.ensure_one()

        if not self.directory_id.journal_id:
            raise exceptions.Warning('Add default journal in acount conf')
        self.import2bankStatements()

    @api.multi
    def change2error_button(self):
        ''' change the state of the file to error because the file is corrupt.
            Called by pressing 'corrupt file?' button.

            :return None:
        '''
        self.ensure_one()
        self._sate_error_on()

    @api.multi
    def change2draft_button(self):
        ''' undo the file is corrupt to state draft.
            Called by pressing 'cancel corrupt file' button.

            :return None:
        '''
        self.ensure_one()
        self.write({'state': 'draft'})

    ##############################
    #          function          #
    ##############################
    @api.multi
    def import2bankStatements(self):
        ''' convert the file to a record of model bankStatment.

            :returns bool:
                - True if the convert was succeed
                - False otherwise
        '''
        self.ensure_one()

        try:
            values = {
                'journal_id': self.directory_id.journal_id.id,
                'data_file': self.files}
            bs_imoprt_obj = self.env['account.bank.statement.import']
            bank_wiz_imp = bs_imoprt_obj.create(values)
            bank_wiz_imp.import_file()
            self._state_finish_on()
            self._add_bankStatement_ref()
            self._remove_binary_file()
            _logger.info("[OK] import file '%s' to bank Statements",
                         (self.filename))
            return True
        except:
            _logger.info("[FAIL] import file '%s' to bank Statements",
                         (self.filename))
            return False

    @api.multi
    def _add_bankStatement_ref(self):
        ''' private function that add the reference to bank statement.

            :returns None:
        '''
        bs = self.env['account.bank.statement'].search([
            ['state', '=', 'draft'],
            ['create_uid', '=', self.env.uid]])
        self.write({'bankStatment_id': max(bs).id})

    @api.multi
    def _remove_binary_file(self):
        ''' private function that remove the binary file.
            the binary file is already convert to bank statment attachment.

            :returns None:
        '''
        self.write({'files': None})

    @api.multi
    def _state_finish_on(self):
        ''' private function that change state to finish

            :returns: None
        '''
        self.ensure_one()
        self.write({'state': 'finish'})

    def _sate_error_on(self):
        ''' private function that change state to error

            :returns: None
        '''
        self.ensure_one()
        self.write({'state': 'error'})
