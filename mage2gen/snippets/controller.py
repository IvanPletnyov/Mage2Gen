# A Magento 2 module generator library
# Copyright (C) 2016 Maikel Martens
# Copyright (C) 2016 Derrick Heesbeen Added Ajax Controller
#
# This file is part of Mage2Gen.
#
# Mage2Gen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
import os
from .. import Module, Phpclass, Phpmethod, Xmlnode, StaticFile, Snippet, SnippetParam, Readme

class ControllerSnippet(Snippet):
	description = """
	Controller is used to serve a request path. A request path look like this:

		www.yourmagentoinstallation.com/frontname/section/action

	- **frontname:** Configured in the router.xml and must be unique.
	- **section:** Is a subfolder or folders to the action class.
	- **action:** An action class that will execute the reqeust.

	This snippet will also create a layout.xml, Block and phtml for the action.
	"""

	snippet_label = 'Controller'

	def add(self, frontname='', section='index', action='index', adminhtml=False, ajax=False, extra_params=None, top_level_menu=True):
		if not frontname:
			frontname = '{}_{}'.format(self._module.package.lower(),self._module.name.lower())
		file = 'etc/{}/routes.xml'.format('adminhtml' if adminhtml else 'frontend')

		# Create config router
		module = Xmlnode('module', attributes={'name': self.module_name})
		if adminhtml:
			module.attributes['before'] = 'Magento_Backend'

		config = Xmlnode('config', attributes={'xsi:noNamespaceSchemaLocation':"urn:magento:framework:App/etc/routes.xsd"}, nodes=[
			Xmlnode('router', attributes={'id': 'admin' if adminhtml else 'standard'}, nodes=[
				Xmlnode('route', attributes={'id': frontname, 'frontName': frontname}, nodes=[
					module
				])
			])
		])
		self.add_xml(file, config)

		# Create controller
		controller_class = ['Controller']
		if adminhtml:
			controller_class.append('Adminhtml')
		controller_class.append(section)
		controller_class.append(action)
		controller = Phpclass('\\'.join(controller_class), 'Action', attributes=[
			'/**\n\t * @var PageFactory\n\t */\n\tprivate $resultPageFactory;'
		], dependencies=[
			'Magento\Backend\App\Action' if adminhtml else 'Magento\Framework\App\Action\Action',
			'Magento\\' + ('Backend' if adminhtml else 'Framework') +'\App\Action\Context',
			'Magento\Framework\View\Result\PageFactory',
			'Magento\Framework\Controller\ResultInterface',
			'Magento\Framework\App\Action\HttpGetActionInterface'
		], implements=[
			'HttpGetActionInterface'
		])

		# generate construct
		if ajax:
			controller.attributes.extend([
				'/**\n\t * @var Data\n\t */\n\tprivate $jsonHelper;',
				'/**\n\t * @var LoggerInterface\n\t */\n\tprivate $logger;'
			])
			controller.dependencies.extend([
				'Magento\Framework\Json\Helper\Data',
				'Psr\Log\LoggerInterface'
			])

			controller.add_method(Phpmethod(
				'__construct',
				params=[
					'Context $context',
					'PageFactory $resultPageFactory',
					'Data $jsonHelper',
					'LoggerInterface $logger',
				],
				body="""$this->resultPageFactory = $resultPageFactory;
					$this->jsonHelper = $jsonHelper;
					$this->logger = $logger;
					parent::__construct($context);
				""",
				docstring=[
					'@param Context $context',
					'@param Data $jsonHelper',
				]
			))
		else:
			controller.add_method(Phpmethod(
				'__construct',
				params=[
					'Context $context',
					'PageFactory $resultPageFactory'
				],
				body="""$this->resultPageFactory = $resultPageFactory;
					parent::__construct($context);
				""",
				docstring=[
					'@param Context $context',
					'@param PageFactory $resultPageFactory',
				]
			))

		# generate execute method
		if ajax:
			execute_body = """try {
			    return $this->jsonResponse(['your response']);
			} catch (\Exception $e) {
			    $this->logger->critical($e);
			    return $this->jsonResponse(['error_message' => $e->getMessage()]);
			}
        	"""
		else:
			execute_body = 'return $this->resultPageFactory->create();'

		controller.add_method(Phpmethod(
			'execute',
			body=execute_body,
			docstring=[
				'Execute view action',
				'',
				'@return ResultInterface',
			]
		))

		# generate jsonResponse method
		if ajax:
			controller.add_method(Phpmethod(
				'jsonResponse',
				access=Phpmethod.PRIVATE,
				params=["array $response = []"],
				body="""
				return $this->getResponse()->representJson(
				    $this->jsonHelper->jsonEncode($response)
				);""",
				docstring=[
					'Create json response',
					'',
					'@param array $response\n\t * '
					'@return ResultInterface',
				]
			))

		self.add_class(controller)

		if ajax:
			return
		else:
			# create block
			block_class = ['Block']
			if adminhtml:
				block_class.append('Adminhtml')
			block_class.append(section)
			block_class.append(action)

			block = Phpclass('\\'.join(block_class), extends='Template', dependencies=[
				'Magento\Backend\Block\Template' if adminhtml else 'Magento\Framework\View\Element\Template',
				'Magento\Backend\Block\Template\Context' if adminhtml else 'Magento\Framework\View\Element\Template\Context'
			])

			block.add_method(Phpmethod(
				'__construct',
				params=[
					'Context $context',
					'array $data = []',
				],
				body="""parent::__construct($context, $data);""",
				docstring=[
					'@param Context $context',
					'@param array $data',
				]
			))

			self.add_class(block)

			# Add layout xml
			layout_xml = Xmlnode('page', attributes={'layout':"admin-1column" if adminhtml else "1column", 'xsi:noNamespaceSchemaLocation':"urn:magento:framework:View/Layout/etc/page_configuration.xsd"}, nodes=[
				Xmlnode('body', nodes=[
					Xmlnode('referenceContainer', attributes={'name': 'content'}, nodes=[
						Xmlnode('block', attributes={
							'name': "{}.{}".format(section, action), 
							'class': block.class_namespace,
							'template': "{}::{}/{}.phtml".format(self.module_name, section, action)
						})
					])
				])
			])
			path = os.path.join('view', 'adminhtml' if adminhtml else 'frontend', 'layout', "{}_{}_{}.xml".format(frontname, section, action))
			self.add_xml(path, layout_xml)

			# add template file
			path = os.path.join('view', 'adminhtml' if adminhtml else 'frontend', 'templates')
			self.add_static_file(path, StaticFile("{}/{}.phtml".format(section, action),body="Hello {}/{}.phtml".format(section, action)))

			if adminhtml:
				# create menu.xml
				top_level_menu_node = False
				if top_level_menu:
					top_level_menu_node = Xmlnode('add', attributes={
						'id': "{}::top_level".format(self._module.package),
						'title': self._module.package,
						'module': self.module_name,
						'sortOrder': 9999,
						'resource': 'Magento_Backend::content',
					})

				self.add_xml('etc/adminhtml/menu.xml', Xmlnode('config', attributes={
					'xsi:noNamespaceSchemaLocation': "urn:magento:module:Magento_Backend:etc/menu.xsd"}, nodes=[
					Xmlnode('menu', nodes=[
						top_level_menu_node,
						Xmlnode('add', attributes={
							'id': '{}::{}_{}'.format(self.module_name, section, action),
							'title': "{} {}".format(section.replace('_', ' '), action.replace('_', ' ')),
							'module': self.module_name,
							'sortOrder': 9999,
							'resource': '{}::{}_{}'.format(self.module_name, section, action),
							'parent': '{}::top_level'.format(self._module.package,frontname),
							'action': '{}/{}/{}'.format(frontname, section, action)
						})
					])
				]))


				acl_xml = Xmlnode('config', attributes={'xmlns:xsi':'http://www.w3.org/2001/XMLSchema-instance','xsi:noNamespaceSchemaLocation':"urn:magento:framework:Acl/etc/acl.xsd"}, nodes=[
					Xmlnode('acl',nodes=[
						Xmlnode('resources',nodes=[
							Xmlnode('resource',attributes={'id':'Magento_Backend::admin'},nodes=[
								Xmlnode('resource',attributes={'id':'{}::{}'.format(self.module_name, frontname),'title':'{}'.format(frontname.replace('_', ' ')),'sortOrder':"10"}, nodes=[
									Xmlnode('resource',attributes={'id':'{}::{}_{}'.format(self.module_name, section, action),'title':'{} {}'.format(section.replace('_', ' '), action.replace('_', ' ')),'sortOrder':"10"}),
								])
							])
						])
					])
				])

				self.add_xml('etc/acl.xml', acl_xml)

		self.add_static_file(
			'.',
			Readme(
				specifications=" - Controller\n\t- {} > {}/{}/{}".format('adminhtml' if adminhtml else 'frontend', frontname, section, action),
			)
		)


	@classmethod
	def params(cls):
		return [
			SnippetParam(name='frontname', required=False, description='On empty uses module name in lower case',
				regex_validator= r'^[a-z]{1}\w+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.',
				repeat=True),
			SnippetParam(name='section', required=True, default='index',
				regex_validator= r'^[a-z]{1}\w+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.',
				repeat=True),
			SnippetParam(name='action', required=True, default='index',
				regex_validator= r'^[a-z]{1}\w+$',
				error_message='Only lowercase alphanumeric and underscore characters are allowed, and need to start with a alphabetic character.'),
			SnippetParam(name='adminhtml', yes_no=True),
			SnippetParam(name='ajax', yes_no=True),
			SnippetParam(
				name='top_level_menu',
				yes_no=True,
				default=True,
				repeat=True
			)
		]
