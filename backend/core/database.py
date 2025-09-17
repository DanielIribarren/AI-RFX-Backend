"""
🔌 Database Client V3.0 - Budy AI Schema Compatible
Centralized database operations adapted to the new normalized budy-ai-schema.sql structure
"""
from typing import Optional, Dict, Any, List, Union
from supabase import create_client, Client
from backend.core.config import get_database_config
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Enhanced Supabase client for V2.0 English schema with connection management"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._config = get_database_config()
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client instance"""
        if self._client is None:
            try:
                self._client = create_client(
                    self._config.url,
                    self._config.anon_key
                )
                logger.info("✅ Database client connected successfully")
            except Exception as e:
                logger.error(f"❌ Failed to connect to database: {e}")
                raise
        return self._client
    
    def health_check(self) -> bool:
        """Check database connection health using budy-ai-schema"""
        try:
            # Test with projects table (main table in new schema)
            response = self.client.table("projects").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # ========================
    # ORGANIZATION OPERATIONS (UPDATED FROM COMPANIES)
    # ========================
    
    def insert_organization(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new organization (updated from company)"""
        try:
            if 'id' not in org_data:
                org_data['id'] = str(uuid4())
            
            # Set defaults for new organization
            if 'plan_type' not in org_data:
                org_data['plan_type'] = 'free'
            if 'default_currency' not in org_data:
                org_data['default_currency'] = 'USD'
            if 'language_preference' not in org_data:
                org_data['language_preference'] = 'es'
            
            response = self.client.table("organizations").insert(org_data).execute()
            if response.data:
                logger.info(f"✅ Organization inserted: {org_data.get('name')} (ID: {response.data[0]['id']})")
                return response.data[0]
            else:
                raise Exception("No data returned from organization insert")
        except Exception as e:
            logger.error(f"❌ Failed to insert organization: {e}")
            raise
    
    def get_organization_by_id(self, org_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get organization by ID"""
        try:
            response = self.client.table("organizations")\
                .select("*")\
                .eq("id", str(org_id))\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get organization {org_id}: {e}")
            return None
    
    def get_organization_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get organization by slug"""
        try:
            response = self.client.table("organizations")\
                .select("*")\
                .eq("slug", slug)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get organization by slug {slug}: {e}")
            return None
    
    # ========================
    # USER OPERATIONS (UPDATED FROM REQUESTERS)
    # ========================
    
    def insert_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new user (updated from requester)"""
        try:
            if 'id' not in user_data:
                user_data['id'] = str(uuid4())
            
            # Set defaults
            if 'language_preference' not in user_data:
                user_data['language_preference'] = 'es'
            if 'timezone' not in user_data:
                user_data['timezone'] = 'UTC'
            if 'is_active' not in user_data:
                user_data['is_active'] = True
            
            response = self.client.table("users").insert(user_data).execute()
            if response.data:
                logger.info(f"✅ User inserted: {user_data.get('email')} (ID: {response.data[0]['id']})")
                return response.data[0]
            else:
                raise Exception("No data returned from user insert")
        except Exception as e:
            logger.error(f"❌ Failed to insert user: {e}")
            raise
    
    def get_user_by_id(self, user_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        try:
            response = self.client.table("users")\
                .select("*")\
                .eq("id", str(user_id))\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get user {user_id}: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        try:
            response = self.client.table("users")\
                .select("*")\
                .eq("email", email)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get user by email {email}: {e}")
            return None
    
    # ========================
    # PROJECT OPERATIONS (UPDATED FROM RFX)
    # ========================
    
    def insert_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new project (formerly RFX)"""
        try:
            if 'id' not in project_data:
                project_data['id'] = str(uuid4())
            
            # Generate project number if not provided
            if 'project_number' not in project_data:
                from datetime import datetime
                project_data['project_number'] = f"PROJ-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
            
            # Set defaults
            if 'status' not in project_data:
                project_data['status'] = 'draft'
            if 'project_type' not in project_data:
                project_data['project_type'] = 'general'
            if 'currency' not in project_data:
                project_data['currency'] = 'USD'
            if 'priority' not in project_data:
                project_data['priority'] = 3
            
            response = self.client.table("projects").insert(project_data).execute()
            if response.data:
                logger.info(f"✅ Project inserted: {project_data.get('name')} (ID: {response.data[0]['id']})")
                return response.data[0]
            else:
                raise Exception("No data returned from project insert")
        except Exception as e:
            logger.error(f"❌ Failed to insert project: {e}")
            raise
    
    def get_project_by_id(self, project_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get project by ID with full context"""
        try:
            response = self.client.table("projects")\
                .select("*, organizations(*), users!projects_created_by_fkey(*)")\
                .eq("id", str(project_id))\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get project {project_id}: {e}")
            return None
    
    def get_projects_by_organization(self, org_id: Union[str, UUID], 
                                   limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get projects for an organization with pagination"""
        try:
            response = self.client.table("projects")\
                .select("*, organizations(*), users!projects_created_by_fkey(*)")\
                .eq("organization_id", str(org_id))\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            logger.info(f"✅ Retrieved {len(response.data) if response.data else 0} projects for org {org_id}")
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get projects for organization {org_id}: {e}")
            return []
    
    def get_latest_projects(self, org_id: Union[str, UUID] = None, 
                          limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get latest projects with organization context"""
        try:
            query = self.client.table("projects")\
                .select("*, organizations(*), users!projects_created_by_fkey(*)")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)
            
            if org_id:
                query = query.eq("organization_id", str(org_id))
            
            response = query.execute()
            
            logger.info(f"✅ Retrieved {len(response.data) if response.data else 0} latest projects")
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get latest projects: {e}")
            return []
    
    def update_project_status(self, project_id: Union[str, UUID], status: str) -> bool:
        """Update project status"""
        try:
            from datetime import datetime
            response = self.client.table("projects")\
                .update({"status": status, "updated_at": datetime.now().isoformat()})\
                .eq("id", str(project_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Project status updated: {project_id} -> {status}")
                return True
            else:
                logger.warning(f"⚠️ No project found to update: {project_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update project status: {e}")
            raise
    
    def update_project_data(self, project_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update project data fields"""
        try:
            logger.info(f"🔄 Updating project data for: {project_id}")
            
            # Define allowed fields to update based on budy-ai-schema projects table
            allowed_fields = {
                "name", "description", "client_name", "client_email", "client_phone", 
                "client_company", "client_type", "service_date", "service_location", 
                "estimated_attendees", "service_duration_hours", "estimated_budget", 
                "currency", "deadline", "tags", "priority", "status"
            }
            
            # Filter update_data to only include allowed fields
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not filtered_data:
                logger.warning(f"⚠️ No valid fields to update for project {project_id}")
                logger.warning(f"⚠️ Attempted fields: {list(update_data.keys())}")
                return False
            
            # Add updated_at timestamp
            from datetime import datetime
            filtered_data['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"🔄 Executing project update with fields: {list(filtered_data.keys())}")
            
            response = self.client.table("projects")\
                .update(filtered_data)\
                .eq("id", str(project_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Project data updated successfully: {project_id}")
                return True
            else:
                logger.warning(f"⚠️ No project found to update: {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update project data: {e}")
            raise
    
    # ========================
    # PROJECT ITEMS OPERATIONS (UPDATED FROM RFX_PRODUCTS)
    # ========================
    
    def insert_project_items(self, project_id: Union[str, UUID], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert project items (formerly RFX products)"""
        try:
            if not items:
                logger.warning(f"No items to insert for project {project_id}")
                return []
            
            items_data = []
            for i, item in enumerate(items):
                item_data = item.copy()
                item_data['project_id'] = str(project_id)
                if 'id' not in item_data:
                    item_data['id'] = str(uuid4())
                
                # Ensure required fields - map from legacy fields if needed
                if 'name' not in item_data:
                    if 'product_name' in item_data:
                        item_data['name'] = item_data['product_name']
                    else:
                        logger.warning(f"Item {i} missing name, skipping")
                        continue
                
                if 'quantity' not in item_data:
                    item_data['quantity'] = 1
                
                if 'unit_of_measure' not in item_data:
                    item_data['unit_of_measure'] = item_data.get('unit', 'pieces')
                
                # Map legacy pricing fields
                if 'unit_price' not in item_data and 'estimated_unit_price' in item_data:
                    item_data['unit_price'] = item_data['estimated_unit_price']
                
                if 'total_price' not in item_data and 'total_estimated_cost' in item_data:
                    item_data['total_price'] = item_data['total_estimated_cost']
                
                # Clean any None values
                for key, value in list(item_data.items()):
                    if value is None and key not in ['unit_price', 'total_price', 'source_document_id', 'description', 'notes']:
                        del item_data[key]
                
                items_data.append(item_data)
                logger.debug(f"✅ Prepared item {i}: {item_data.get('name')} (ID: {item_data['id']})")
            
            if not items_data:
                logger.warning(f"No valid items to insert for project {project_id}")
                return []
            
            logger.info(f"🔄 Inserting {len(items_data)} items for project {project_id}")
            response = self.client.table("project_items").insert(items_data).execute()
            
            if response.data:
                logger.info(f"✅ {len(response.data)} project items inserted for project {project_id}")
                for item in response.data:
                    logger.debug(f"   - {item.get('name')} (ID: {item.get('id')})")
                return response.data
            else:
                logger.error(f"❌ No data returned after inserting items for project {project_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to insert project items for {project_id}: {e}")
            logger.error(f"❌ Items data that failed: {items_data if 'items_data' in locals() else 'N/A'}")
            raise
    
    def get_project_items(self, project_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all items for a project"""
        try:
            response = self.client.table("project_items")\
                .select("*")\
                .eq("project_id", str(project_id))\
                .order("sort_order")\
                .execute()
            
            items = response.data or []
            logger.info(f"✅ Found {len(items)} items for project {project_id}")
            return items
        except Exception as e:
            logger.error(f"❌ Failed to get project items for {project_id}: {e}")
            return []
    
    def update_project_item_cost(self, project_id: Union[str, UUID], item_id: str, unit_price: float) -> bool:
        """Update unit price for a specific project item"""
        try:
            from datetime import datetime
            response = self.client.table("project_items")\
                .update({"unit_price": unit_price, "updated_at": datetime.now().isoformat()})\
                .eq("project_id", str(project_id))\
                .eq("id", item_id)\
                .execute()
            
            if response.data:
                logger.info(f"✅ Updated item {item_id} cost to ${unit_price:.2f}")
                return True
            else:
                logger.warning(f"⚠️ No item found to update: Project {project_id}, Item {item_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update item cost: {e}")
            return False
    
    # ========================
    # SUPPLIER OPERATIONS
    # ========================
    
    def get_suppliers(self, category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get suppliers, optionally filtered by category"""
        try:
            query = self.client.table("suppliers").select("*")
            
            if active_only:
                query = query.eq("is_active", True)
            
            if category:
                query = query.eq("category", category)
            
            response = query.order("rating", desc=True).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get suppliers: {e}")
            return []
    
    def get_product_catalog(self, supplier_id: Optional[Union[str, UUID]] = None, 
                          category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get product catalog, optionally filtered by supplier or category"""
        try:
            query = self.client.table("product_catalog")\
                .select("*, suppliers(*)")\
                .eq("is_active", True)
            
            if supplier_id:
                query = query.eq("supplier_id", str(supplier_id))
            
            if category:
                query = query.eq("category", category)
            
            response = query.order("name").execute()
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get product catalog: {e}")
            return []
    
    def get_product_by_name(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Get product information by name from catalog"""
        try:
            response = self.client.table("product_catalog")\
                .select("*, suppliers(*)")\
                .ilike("name", f"%{product_name}%")\
                .eq("is_active", True)\
                .limit(1)\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.warning(f"⚠️ Could not find product {product_name} in catalog: {e}")
            return None
    
    # ========================
    # QUOTES OPERATIONS (UPDATED FROM DOCUMENTS)
    # ========================
    
    def insert_quote(self, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert generated quote (formerly document)"""
        try:
            if 'id' not in quote_data:
                quote_data['id'] = str(uuid4())
            
            # Generate quote number if not provided
            if 'quote_number' not in quote_data:
                from datetime import datetime
                quote_number = f"QTE-{datetime.now().strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"
                quote_data['quote_number'] = quote_number
            
            # Set defaults
            if 'status' not in quote_data:
                quote_data['status'] = 'draft'
            if 'version' not in quote_data:
                quote_data['version'] = 1
            if 'currency' not in quote_data:
                quote_data['currency'] = 'USD'
            if 'generation_method' not in quote_data:
                quote_data['generation_method'] = 'ai_assisted'
            
            # Map legacy document fields to quote fields if needed
            if any(legacy_field in quote_data for legacy_field in ['rfx_id', 'content_html', 'total_cost']):
                quote_data = self._map_document_to_quote_fields(quote_data)
            
            response = self.client.table("quotes").insert(quote_data).execute()
            if response.data:
                logger.info(f"✅ Quote inserted: {quote_data.get('quote_number')} (ID: {response.data[0]['id']})")
                return response.data[0]
            else:
                raise Exception("No data returned from quote insert")
        except Exception as e:
            logger.error(f"❌ Failed to insert quote: {e}")
            raise
    
    def _map_document_data_to_v2(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map legacy Spanish field names to V2.0 English schema"""
        # Column mapping: Spanish (legacy) -> English (V2.0)
        field_mapping = {
            'contenido_html': 'content_html',
            'contenido_markdown': 'content_markdown', 
            'tipo_documento': 'document_type',
            'costo_total': 'total_cost',
            'fecha_creacion': 'created_at',
            'metadatos': 'metadata',
            'costos_desglosados': 'itemized_costs',
            'subtotal': 'subtotal',
            'impuestos': 'tax_amount',
            'plantilla_usada': 'template_used',

            'url_archivo': 'file_url',
            'ruta_archivo': 'file_path',
            'aprobado_por': 'approved_by',
            'fecha_aprobacion': 'approved_at'
        }
        
        mapped_data = {}
        
        # Map known fields
        for legacy_key, v2_key in field_mapping.items():
            if legacy_key in doc_data:
                mapped_data[v2_key] = doc_data[legacy_key]
        
        # Copy unmapped fields as-is (assume they're already in V2.0 format)
        for key, value in doc_data.items():
            if key not in field_mapping and key not in mapped_data:
                # Convert UUIDs to strings for JSON serialization
                if hasattr(value, '__class__') and 'UUID' in str(value.__class__):
                    mapped_data[key] = str(value)
                else:
                    mapped_data[key] = value
        
        # Ensure required V2.0 fields have defaults
        if 'document_type' not in mapped_data:
            mapped_data['document_type'] = 'proposal'
        if 'version' not in mapped_data:
            mapped_data['version'] = 1

            
        logger.debug(f"🔄 Mapped document data: {list(field_mapping.keys())} -> {list(mapped_data.keys())}")
        return mapped_data
    
    def get_quote_by_id(self, quote_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get quote by ID"""
        try:
            response = self.client.table("quotes")\
                .select("*, projects(*), organizations(*)")\
                .eq("id", str(quote_id))\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"❌ Failed to get quote {quote_id}: {e}")
            return None
    
    def get_quotes_by_project(self, project_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all quotes for a project"""
        try:
            response = self.client.table("quotes")\
                .select("*")\
                .eq("project_id", str(project_id))\
                .order("created_at", desc=True)\
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get quotes for project {project_id}: {e}")
            return []
    
    # ========================
    # HISTORY & AUDIT
    # ========================
    
    def insert_rfx_history(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert RFX history event"""
        try:
            if 'id' not in history_data:
                history_data['id'] = str(uuid4())
            
            response = self.client.table("rfx_history").insert(history_data).execute()
            if response.data:
                logger.debug(f"✅ RFX history event inserted: {history_data['event_type']}")
                return response.data[0]
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to insert RFX history: {e}")
            raise
    
    def get_rfx_history_events(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all history events for an RFX"""
        try:
            response = self.client.table("rfx_history")\
                .select("*")\
                .eq("rfx_id", str(rfx_id))\
                .order("performed_at", desc=True)\
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get RFX history for {rfx_id}: {e}")
            return []
    
    # ========================
    # STORAGE OPERATIONS
    # ========================
    
    def upload_file_to_storage(self, bucket: str, file_path: str, file_data: bytes) -> str:
        """Upload file to Supabase storage"""
        try:
            # Create bucket if it doesn't exist
            try:
                self.client.storage.create_bucket(bucket)
            except Exception:
                pass  # Bucket might already exist
            
            # Upload file
            response = self.client.storage.from_(bucket).upload(
                file_path, 
                file_data,
                {"content-type": "application/pdf"}
            )
            
            # Get public URL
            public_url = self.client.storage.from_(bucket).get_public_url(file_path)
            logger.info(f"✅ File uploaded to storage: {file_path}")
            return public_url
            
        except Exception as e:
            logger.error(f"❌ Failed to upload file to storage: {e}")
            raise
    
    # ========================
    # SMART RFX LOOKUP METHODS
    # ========================
    
    def find_rfx_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        🔍 Smart RFX lookup: Try UUID first, then search by requester name, then company name
        
        Args:
            identifier: Could be UUID, requester name, or company name
            
        Returns:
            RFX record if found, None otherwise
        """
        try:
            logger.info(f"🔍 Smart RFX lookup for identifier: '{identifier}'")
            
            # 1. Try UUID first (fastest)
            try:
                import uuid as _uuid
                _ = _uuid.UUID(identifier)
                logger.info(f"✅ Identifier '{identifier}' is valid UUID, direct lookup")
                return self.get_rfx_by_id(identifier)
            except (ValueError, TypeError):
                logger.info(f"🔄 Identifier '{identifier}' is not UUID, trying name-based search")
            
            # 2. Search by requester name
            requester_result = self._find_rfx_by_requester_name(identifier)
            if requester_result:
                logger.info(f"✅ Found RFX by requester name: {requester_result['id']}")
                return requester_result
            
            # 3. Search by company name
            company_result = self._find_rfx_by_company_name(identifier)
            if company_result:
                logger.info(f"✅ Found RFX by company name: {company_result['id']}")
                return company_result
            
            logger.warning(f"❌ No RFX found for identifier: '{identifier}'")
            return None
            
        except Exception as e:
            logger.error(f"❌ Error in smart RFX lookup for '{identifier}': {e}")
            return None
    
    def _find_rfx_by_requester_name(self, requester_name: str) -> Optional[Dict[str, Any]]:
        """Find RFX by requester name (case insensitive)"""
        try:
            # First, find requester by name
            requester_response = self.client.table("requesters")\
                .select("id, name, company_id")\
                .eq("name", requester_name)\
                .execute()
            
            if not requester_response.data:
                # Try fuzzy search
                requester_response = self.client.table("requesters")\
                    .select("id, name, company_id")\
                    .ilike("name", f"%{requester_name}%")\
                    .execute()
            
            if requester_response.data:
                # Found requester(s), now find their RFX
                for requester in requester_response.data:
                    rfx_response = self.client.table("rfx_v2")\
                        .select("*, companies(*), requesters(*)")\
                        .eq("requester_id", requester["id"])\
                        .order("created_at", desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if rfx_response.data:
                        logger.info(f"Found RFX by requester name '{requester_name}': {rfx_response.data[0]['id']}")
                        return rfx_response.data[0]
                
            return None
        except Exception as e:
            logger.error(f"❌ Error searching RFX by requester name '{requester_name}': {e}")
            return None
    
    def _find_rfx_by_company_name(self, company_name: str) -> Optional[Dict[str, Any]]:
        """Find RFX by company name (case insensitive)"""
        try:
            # First, find company by name
            company_response = self.client.table("companies")\
                .select("id, name")\
                .eq("name", company_name)\
                .execute()
            
            if not company_response.data:
                # Try fuzzy search
                company_response = self.client.table("companies")\
                    .select("id, name")\
                    .ilike("name", f"%{company_name}%")\
                    .execute()
            
            if company_response.data:
                # Found company(s), now find their RFX
                for company in company_response.data:
                    rfx_response = self.client.table("rfx_v2")\
                        .select("*, companies(*), requesters(*)")\
                        .eq("company_id", company["id"])\
                        .order("created_at", desc=True)\
                        .limit(1)\
                        .execute()
                    
                    if rfx_response.data:
                        logger.info(f"Found RFX by company name '{company_name}': {rfx_response.data[0]['id']}")
                        return rfx_response.data[0]
                
            return None
        except Exception as e:
            logger.error(f"❌ Error searching RFX by company name '{company_name}': {e}")
            return None

    # ========================
    # LEGACY COMPATIBILITY HELPERS
    # ========================
    
    def _get_or_create_company_for_requester(self, requester_data: Dict[str, Any]) -> str:
        """Get or create a company for the requester"""
        try:
            # Extract company name from requester data
            company_name = self._infer_company_name(requester_data)
            
            # Check if company already exists
            existing = self.client.table("companies")\
                .select("*")\
                .eq("name", company_name)\
                .execute()
            
            if existing and existing.data:
                return existing.data[0]["id"]
            else:
                # Create new company
                company_data = {
                    "name": company_name,
                    "email": requester_data.get("email", "").split('@')[1] if '@' in requester_data.get("email", "") else None
                }
                
                created_company = self.insert_company(company_data)
                return created_company["id"]
                
        except Exception as e:
            logger.error(f"❌ Failed to get/create company: {e}")
            raise
    
    def _infer_company_name(self, requester_data: Dict[str, Any]) -> str:
        """Infer company name from requester data"""
        requester_name = requester_data.get("name", "")
        email = requester_data.get("email", "")
        
        # If requester name looks like a company name, use it
        if any(word in requester_name.lower() for word in ["inc", "corp", "ltd", "llc", "sa", "solutions", "tech", "company"]):
            return requester_name
        
        # Otherwise, try to infer from email domain
        if '@' in email:
            domain = email.split('@')[1]
            company_name = domain.split('.')[0].title()
            return f"{company_name} Corporation"
        
        # Fallback
        return f"{requester_name} Company"
    
    # ========================
    # UPDATE METHODS FOR NORMALIZED SCHEMA
    # ========================
    
    def update_requester(self, requester_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update requester information"""
        try:
            response = self.client.table("requesters")\
                .update(update_data)\
                .eq("id", str(requester_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Requester updated: {requester_id}")
                return True
            else:
                logger.warning(f"⚠️ No requester found to update: {requester_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update requester: {e}")
            raise
    
    def update_company(self, company_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update company information"""
        try:
            response = self.client.table("companies")\
                .update(update_data)\
                .eq("id", str(company_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Company updated: {company_id}")
                return True
            else:
                logger.warning(f"⚠️ No company found to update: {company_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update company: {e}")
            raise

    def update_rfx_product(self, product_id: Union[str, UUID], rfx_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update RFX product information"""
        try:
            response = self.client.table("rfx_products")\
                .update(update_data)\
                .eq("id", str(product_id))\
                .eq("rfx_id", str(rfx_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Product updated: {product_id} for RFX {rfx_id}")
                return True
            else:
                logger.warning(f"⚠️ No product found to update: {product_id} in RFX {rfx_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update product: {e}")
            raise

    # ========================
    # LEGACY COMPATIBILITY
    # ========================
    
    # Legacy method aliases for backwards compatibility
    def insert_client(self, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy alias for insert_requester"""
        return self.insert_requester(client_data)
    
    def save_generated_document(self, doc_data: Dict[str, Any]) -> str:
        """Legacy alias for insert_generated_document returning ID with enhanced error logging"""
        try:
            logger.debug(f"🔍 save_generated_document called with keys: {list(doc_data.keys())}")
            
            # Validate required fields before attempting database operation
            required_fields = ["id", "rfx_id", "document_type", "content_html"]
            missing_fields = [field for field in required_fields if field not in doc_data or doc_data[field] is None]
            
            if missing_fields:
                logger.error(f"❌ Missing required fields for document: {missing_fields}")
                logger.error(f"❌ Available fields: {list(doc_data.keys())}")
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Check for valid UUID format
            try:
                from uuid import UUID
                UUID(doc_data["id"])
                UUID(doc_data["rfx_id"])
            except ValueError as e:
                logger.error(f"❌ Invalid UUID format: {e}")
                raise ValueError(f"Invalid UUID format in document data: {e}")
            
            result = self.insert_generated_document(doc_data)
            return result.get("id", "")
        except Exception as e:
            logger.error(f"❌ save_generated_document failed: {e}")
            logger.error(f"❌ Problematic document data: {doc_data}")
            raise


# Global database client instance
_db_client: Optional[DatabaseClient] = None


def get_database_client() -> DatabaseClient:
    """Get global database client instance"""
    global _db_client
    if _db_client is None:
        _db_client = DatabaseClient()
    return _db_client


# Helper function for document to quote mapping
def _map_document_to_quote_fields(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
    """Map legacy document fields to new quote structure"""
    quote_data = doc_data.copy()
    
    field_mapping = {
        'rfx_id': 'project_id',
        'content_html': 'html_content',
        'total_cost': 'total_amount',
        'created_by': 'created_by'
    }
    
    for old_key, new_key in field_mapping.items():
        if old_key in quote_data:
            quote_data[new_key] = quote_data.pop(old_key)
    
    # Ensure subtotal is set
    if 'subtotal' not in quote_data and 'total_amount' in quote_data:
        quote_data['subtotal'] = quote_data['total_amount']
    
    return quote_data

# Add legacy compatibility methods
DatabaseClient._map_document_to_quote_fields = _map_document_to_quote_fields

# Legacy method aliases
def insert_rfx(self, rfx_data: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy alias: RFX -> Project"""
    # Map legacy RFX fields to new project fields
    project_data = self._map_rfx_to_project(rfx_data)
    return self.insert_project(project_data)

def get_rfx_by_id(self, rfx_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
    """Legacy alias: RFX -> Project"""
    project = self.get_project_by_id(rfx_id)
    if project:
        return self._map_project_to_rfx(project)
    return None

def get_rfx_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Legacy alias: Get project history"""
    logger.warning("⚠️ get_rfx_history called - requires organization context in new schema")
    return []

def get_latest_rfx(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Legacy alias: Get latest projects"""
    logger.warning("⚠️ get_latest_rfx called - requires organization context in new schema")
    return []

def insert_rfx_products(self, rfx_id: Union[str, UUID], products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Legacy alias: RFX Products -> Project Items"""
    return self.insert_project_items(rfx_id, products)

def get_rfx_products(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
    """Legacy alias: Project Items -> RFX Products"""
    items = self.get_project_items(rfx_id)
    return self._map_items_to_products(items)

def save_generated_document(self, doc_data: Dict[str, Any]) -> str:
    """Legacy alias: Generated Document -> Quote"""
    result = self.insert_quote(doc_data)
    return result.get("id", "")

def get_document_by_id(self, doc_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
    """Legacy alias: Quote -> Document"""
    quote = self.get_quote_by_id(doc_id)
    if quote:
        return self._map_quote_to_document(quote)
    return None

def get_proposals_by_rfx_id(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
    """Legacy alias: Get quotes for project"""
    quotes = self.get_quotes_by_project(rfx_id)
    documents = []
    for quote in quotes:
        document = self._map_quote_to_document(quote)
        documents.append(document)
    return documents

def find_rfx_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
    """Legacy alias: Smart project lookup"""
    project = self.find_project_by_identifier(identifier)
    if project:
        return self._map_project_to_rfx(project)
    return None

def update_rfx_status(self, rfx_id: Union[str, UUID], status: str) -> bool:
    """Legacy alias: Update project status"""
    return self.update_project_status(rfx_id, status)

def update_rfx_data(self, rfx_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
    """Legacy alias: Update project data"""  
    return self.update_project_data(rfx_id, update_data)

# Add legacy methods to DatabaseClient
DatabaseClient.insert_rfx = insert_rfx
DatabaseClient.get_rfx_by_id = get_rfx_by_id
DatabaseClient.get_rfx_history = get_rfx_history
DatabaseClient.get_latest_rfx = get_latest_rfx
DatabaseClient.insert_rfx_products = insert_rfx_products
DatabaseClient.get_rfx_products = get_rfx_products
DatabaseClient.save_generated_document = save_generated_document
DatabaseClient.get_document_by_id = get_document_by_id
DatabaseClient.get_proposals_by_rfx_id = get_proposals_by_rfx_id
DatabaseClient.find_rfx_by_identifier = find_rfx_by_identifier
DatabaseClient.update_rfx_status = update_rfx_status
DatabaseClient.update_rfx_data = update_rfx_data

# Alias for backward compatibility
def get_supabase() -> Client:
    """Get raw Supabase client (for backward compatibility)"""
    return get_database_client().client