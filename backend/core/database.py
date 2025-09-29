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
    """Enhanced Supabase client V3.0 - Hybrid Schema Support (rfx_v2 + budy-ai-schema)"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._config = get_database_config()
        self._schema_mode: Optional[str] = None  # Will be 'legacy' or 'modern'
    
    @property
    def client(self) -> Client:
        """Get or create Supabase client instance"""
        if self._client is None:
            try:
                # Usar service_role_key si está disponible (bypassa RLS), sino anon_key
                api_key = self._config.service_role_key if self._config.service_role_key else self._config.anon_key
                
                if self._config.service_role_key:
                    logger.info("🔑 Using service role key for database operations (bypasses RLS)")
                else:
                    logger.warning("⚠️ Using anon key - RLS policies may block operations")
                
                self._client = create_client(
                    self._config.url,
                    api_key
                )
                logger.info("✅ Database client connected successfully")
                # Auto-detect schema mode
                self._detect_schema_mode()
            except Exception as e:
                logger.error(f"❌ Failed to connect to database: {e}")
                raise
        return self._client
    
    def _detect_schema_mode(self) -> None:
        """Force modern schema mode - legacy support removed"""
        try:
            # Force modern schema only
            response = self.client.table("projects").select("id").limit(1).execute()
            self._schema_mode = "modern"
            logger.info("🆕 Modern schema active (budy-ai-schema)")
        except Exception as e:
            logger.error(f"❌ Modern schema not available: {e}")
            logger.error("💡 Run 'python migrate_to_modern_schema.py' to migrate from legacy schema")
            self._schema_mode = "unknown"
            raise Exception("Modern schema required but not found. Please run migration first.")
    
    @property
    def schema_mode(self) -> str:
        """Get current schema mode"""
        if self._schema_mode is None:
            self._detect_schema_mode()
        return self._schema_mode or "unknown"
    
    def health_check(self) -> bool:
        """Check database connection health - modern schema only"""
        try:
            response = self.client.table("projects").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    # Legacy mapping functions removed - modern schema only
    
    # ========================
    # ORGANIZATION OPERATIONS (UPDATED FROM COMPANIES)
    # ========================
    
    def insert_organization(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new organization (hybrid mode: modern=organizations, legacy=companies)"""
        try:
            if self.schema_mode == "modern":
                # Modern schema: organizations table
                if 'id' not in org_data:
                    org_data['id'] = str(uuid4())
                if 'plan_type' not in org_data:
                    org_data['plan_type'] = 'free'
                if 'default_currency' not in org_data:
                    org_data['default_currency'] = 'USD'
                if 'language_preference' not in org_data:
                    org_data['language_preference'] = 'es'
                
                response = self.client.table("organizations").insert(org_data).execute()
                if response.data:
                    logger.info(f"✅ Organization inserted (modern): {org_data.get('name')} (ID: {response.data[0]['id']})")
                    return response.data[0]
                else:
                    raise Exception("No data returned from organization insert")
            else:
                # Legacy schema: companies table
                company_data = {
                    'id': org_data.get('id', str(uuid4())),
                    'name': org_data.get('name'),
                    'industry': org_data.get('business_sector'),
                    'country': org_data.get('country_code', 'Mexico'),
                    'email': org_data.get('email'),
                    'phone': org_data.get('phone')
                }
                
                response = self.client.table("companies").insert(company_data).execute()
                if response.data:
                    logger.info(f"✅ Organization inserted (legacy): {company_data.get('name')} (ID: {response.data[0]['id']})")
                    return response.data[0]
                else:
                    raise Exception("No data returned from company insert")
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
            
            if response.data:
                user = response.data[0]
                # Build full name from first_name and last_name for compatibility
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                user['name'] = f"{first_name} {last_name}".strip()
                return user
            else:
                return None
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
            
            if response.data:
                user = response.data[0]
                # Build full name from first_name and last_name for compatibility
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                user['name'] = f"{first_name} {last_name}".strip()
                return user
            else:
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get user by email {email}: {e}")
            return None

    def update_user(self, user_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update user information"""
        try:
            from datetime import datetime
            update_data['updated_at'] = datetime.now().isoformat()
            
            response = self.client.table("users")\
                .update(update_data)\
                .eq("id", str(user_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ User updated: {user_id}")
                return True
            else:
                logger.warning(f"⚠️ No user found to update: {user_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update user: {e}")
            return False

    def update_organization(self, org_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update organization information"""
        try:
            from datetime import datetime
            update_data['updated_at'] = datetime.now().isoformat()
            
            response = self.client.table("organizations")\
                .update(update_data)\
                .eq("id", str(org_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Organization updated: {org_id}")
                return True
            else:
                logger.warning(f"⚠️ No organization found to update: {org_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update organization: {e}")
            return False
    
    # ========================
    # PROJECT OPERATIONS (UPDATED FROM RFX)
    # ========================
    
    def insert_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert new project - modern schema only"""
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
        """Get project by ID with full context - modern schema only - OPTIMIZED WITH JOINS"""
        try:
            # SINGLE QUERY with JOINs - much more efficient than 3 separate queries
            response = self.client.table("projects")\
                .select("*, organizations(*), users!created_by(*)")\
                .eq("id", str(project_id))\
                .execute()
            
            if not response.data:
                return None
            
            project = response.data[0]
            
            # Build full name for user compatibility (if user exists)
            if project.get('users'):
                user = project['users']
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                user['name'] = f"{first_name} {last_name}".strip()
            
            logger.debug(f"✅ Retrieved project {project_id} with related data in single query")
            return project
            
        except Exception as e:
            logger.error(f"❌ Failed to get project {project_id}: {e}")
            return None
    
    def get_projects_by_organization(self, org_id: Union[str, UUID], 
                                   limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get projects for an organization with pagination - OPTIMIZED WITH JOINS"""
        try:
            # SINGLE QUERY with JOINs - eliminates N+1 problem for organization projects
            response = self.client.table("projects")\
                .select("*, organizations(*), users!created_by(*)")\
                .eq("organization_id", str(org_id))\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            projects = response.data or []
            
            # Build full name for user compatibility for each project
            for project in projects:
                if project.get('users'):
                    user = project['users']
                    first_name = user.get('first_name', '')
                    last_name = user.get('last_name', '')
                    user['name'] = f"{first_name} {last_name}".strip()
            
            logger.info(f"✅ Retrieved {len(projects)} projects for org {org_id} with related data in single query")
            return projects
        except Exception as e:
            logger.error(f"❌ Failed to get projects for organization {org_id}: {e}")
            return []
    
    def get_latest_projects(self, org_id: Union[str, UUID] = None, 
                          limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get latest projects with organization context - modern schema only - OPTIMIZED WITH JOINS"""
        try:
            # SINGLE QUERY with JOINs - eliminates N+1 problem
            query = self.client.table("projects")\
                .select("*, organizations(*), users!created_by(*)")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)
            
            if org_id:
                query = query.eq("organization_id", str(org_id))
            
            response = query.execute()
            projects = response.data or []
            
            # Build full name for user compatibility for each project
            for project in projects:
                if project.get('users'):
                    user = project['users']
                    first_name = user.get('first_name', '')
                    last_name = user.get('last_name', '')
                    user['name'] = f"{first_name} {last_name}".strip()
            
            logger.info(f"✅ Retrieved {len(projects)} latest projects with related data in single query")
            return projects
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
        """Update project data fields - IMPROVED VALIDATION"""
        try:
            logger.info(f"🔄 Updating project data for: {project_id}")
            logger.debug(f"🔍 Raw update data: {update_data}")
            
            # Define allowed fields to update based on budy-ai-schema projects table
            allowed_fields = {
                "name", "description", "client_name", "client_email", "client_phone", 
                "client_company", "client_type", "service_date", "service_location", 
                "estimated_attendees", "service_duration_hours", "estimated_budget", 
                "currency", "deadline", "tags", "priority", "status"
            }
            
            # STEP 1: Filter by allowed fields
            filtered_by_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not filtered_by_fields:
                logger.warning(f"⚠️ No valid fields to update for project {project_id}")
                logger.warning(f"⚠️ Attempted fields: {list(update_data.keys())}")
                logger.warning(f"⚠️ Allowed fields: {sorted(allowed_fields)}")
                return False
            
            # STEP 2: Filter out None and empty values (avoid NULL inserts)
            meaningful_data = {}
            for key, value in filtered_by_fields.items():
                if value is not None and value != "":
                    # For lists and arrays, check if they're not empty
                    if isinstance(value, (list, tuple)) and len(value) == 0:
                        logger.debug(f"⚠️ Skipping empty array field: {key}")
                        continue
                    meaningful_data[key] = value
                else:
                    logger.debug(f"⚠️ Skipping None/empty field: {key} = {value}")
            
            if not meaningful_data:
                logger.warning(f"⚠️ No meaningful data to update for project {project_id}")
                logger.warning(f"⚠️ All values were None or empty: {filtered_by_fields}")
                return False
            
            # Add updated_at timestamp
            from datetime import datetime
            meaningful_data['updated_at'] = datetime.now().isoformat()
            
            logger.info(f"🔄 Executing project update with {len(meaningful_data)} meaningful fields: {list(meaningful_data.keys())}")
            logger.debug(f"🔍 Final update data: {meaningful_data}")
            
            response = self.client.table("projects")\
                .update(meaningful_data)\
                .eq("id", str(project_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Project data updated successfully: {project_id}")
                logger.debug(f"✅ Updated fields: {list(meaningful_data.keys())}")
                return True
            else:
                logger.warning(f"⚠️ No project found to update: {project_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update project data for {project_id}: {e}")
            logger.error(f"❌ Update data that failed: {update_data}")
            raise
    
    # ========================
    # PROJECT ITEMS OPERATIONS (UPDATED FROM RFX_PRODUCTS)
    # ========================
    
    def insert_project_items(self, project_id: Union[str, UUID], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert project items (formerly RFX products) - IMPROVED VALIDATION"""
        try:
            # STEP 1: Early validation
            if not items:
                logger.warning(f"⚠️ No items provided for project {project_id}")
                return []
            
            if not isinstance(items, list):
                raise ValueError(f"Items must be a list, got {type(items)}")
            
            logger.info(f"🔄 Processing {len(items)} items for project {project_id}")
            
            items_data = []
            skipped_items = []
            
            for i, item in enumerate(items):
                logger.debug(f"🔍 Processing item {i+1}/{len(items)}: {item}")
                
                item_data = item.copy()
                item_data['project_id'] = str(project_id)
                if 'id' not in item_data:
                    item_data['id'] = str(uuid4())
                
                # STEP 2: Validate and map required fields
                item_name = None
                if 'name' in item_data and item_data['name']:
                    item_name = item_data['name']
                elif 'product_name' in item_data and item_data['product_name']:
                    item_name = item_data['product_name']
                    item_data['name'] = item_name
                else:
                    # Instead of silently skipping, log detailed error
                    error_msg = f"Item {i+1} missing required 'name' field. Item data: {item}"
                    logger.error(f"❌ {error_msg}")
                    skipped_items.append({"index": i+1, "reason": "missing_name", "data": item})
                    continue
                
                # Set defaults for other required fields
                if 'quantity' not in item_data or not item_data['quantity']:
                    item_data['quantity'] = 1
                    logger.debug(f"🔧 Set default quantity=1 for item: {item_name}")
                
                if 'unit_of_measure' not in item_data or not item_data['unit_of_measure']:
                    item_data['unit_of_measure'] = item_data.get('unit', 'pieces')
                    logger.debug(f"🔧 Set default unit_of_measure for item: {item_name}")
                
                # Map legacy pricing fields
                if 'unit_price' not in item_data and 'estimated_unit_price' in item_data:
                    item_data['unit_price'] = item_data['estimated_unit_price']
                    logger.debug(f"🔧 Mapped estimated_unit_price -> unit_price for item: {item_name}")
                
                if 'total_price' not in item_data and 'total_estimated_cost' in item_data:
                    item_data['total_price'] = item_data['total_estimated_cost']
                    logger.debug(f"🔧 Mapped total_estimated_cost -> total_price for item: {item_name}")
                
                # Clean None values (but keep important optional fields)
                nullable_fields = {'unit_price', 'total_price', 'source_document_id', 'description', 'validation_notes', 'category'}
                for key, value in list(item_data.items()):
                    if value is None and key not in nullable_fields:
                        del item_data[key]
                        logger.debug(f"🧹 Removed None field '{key}' from item: {item_name}")
                
                items_data.append(item_data)
                logger.debug(f"✅ Prepared item {i+1}: {item_name} (ID: {item_data['id']})")
            
            # STEP 3: Validate final results
            if skipped_items:
                logger.warning(f"⚠️ {len(skipped_items)} items were skipped due to validation errors:")
                for skipped in skipped_items:
                    logger.warning(f"   - Item {skipped['index']}: {skipped['reason']}")
            
            if not items_data:
                error_msg = f"No valid items to insert for project {project_id}. Total provided: {len(items)}, Skipped: {len(skipped_items)}"
                logger.error(f"❌ {error_msg}")
                if skipped_items:
                    logger.error("❌ All items failed validation. Check the item data structure.")
                raise ValueError(error_msg)
            
            # STEP 4: Insert all valid items
            logger.info(f"🔄 Inserting {len(items_data)} valid items for project {project_id}")
            response = self.client.table("project_items").insert(items_data).execute()
            
            if response.data:
                logger.info(f"✅ {len(response.data)} project items inserted successfully for project {project_id}")
                for item in response.data:
                    logger.debug(f"   ✅ {item.get('name')} (ID: {item.get('id')})")
                return response.data
            else:
                raise Exception("No data returned from database after insert operation")
                
        except Exception as e:
            logger.error(f"❌ Failed to insert project items for {project_id}: {e}")
            if 'items_data' in locals():
                logger.error(f"❌ Valid items prepared: {len(items_data)}")
            if 'skipped_items' in locals():
                logger.error(f"❌ Items skipped: {len(skipped_items)}")
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

    def update_project_item(self, item_id: str, project_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update project item data"""
        try:
            from datetime import datetime
            update_data['updated_at'] = datetime.now().isoformat()
            
            response = self.client.table("project_items")\
                .update(update_data)\
                .eq("id", item_id)\
                .eq("project_id", str(project_id))\
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ Project item updated: {item_id}")
                return True
            else:
                logger.warning(f"⚠️ No project item found to update: {item_id} in project {project_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update project item: {e}")
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
    
    def insert_audit_log(self, audit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert audit log event (replaces insert_rfx_history) - uses modern audit_logs table"""
        try:
            if 'id' not in audit_data:
                audit_data['id'] = str(uuid4())
            
            # Ensure required fields for audit_logs schema
            required_fields = ['action', 'table_name', 'record_id', 'organization_id']
            for field in required_fields:
                if field not in audit_data:
                    raise ValueError(f"Missing required field for audit log: {field}")
            
            # Set performed_at if not provided
            if 'performed_at' not in audit_data:
                from datetime import datetime
                audit_data['performed_at'] = datetime.now().isoformat()
            
            response = self.client.table("audit_logs").insert(audit_data).execute()
            if response.data:
                logger.debug(f"✅ Audit log inserted: {audit_data['action']} on {audit_data['table_name']}")
                return response.data[0]
            return {}
        except Exception as e:
            logger.error(f"❌ Failed to insert audit log: {e}")
            raise
    
    def get_project_audit_events(self, project_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all audit events for a project (replaces get_rfx_history_events)"""
        try:
            response = self.client.table("audit_logs")\
                .select("*")\
                .eq("record_id", str(project_id))\
                .eq("table_name", "projects")\
                .order("performed_at", desc=True)\
                .execute()
            
            logger.debug(f"✅ Retrieved {len(response.data or [])} audit events for project {project_id}")
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get audit events for project {project_id}: {e}")
            return []
    
    # Legacy compatibility methods
    def insert_rfx_history(self, history_data: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy alias: insert_rfx_history -> insert_audit_log"""
        logger.warning("⚠️ insert_rfx_history is deprecated, use insert_audit_log instead")
        
        # Convert legacy history format to audit log format
        audit_data = {
            'action': history_data.get('event_type', 'update'),
            'table_name': 'projects',  # Assume projects for legacy compatibility
            'record_id': history_data.get('rfx_id', history_data.get('project_id')),
            'organization_id': history_data.get('organization_id'),
            'user_id': history_data.get('user_id'),
            'user_email': history_data.get('user_email'),
            'action_reason': history_data.get('event_description'),
            'new_values': history_data.get('event_data', {}),
            'ip_address': history_data.get('ip_address'),
            'user_agent': history_data.get('user_agent')
        }
        
        # Remove None values
        audit_data = {k: v for k, v in audit_data.items() if v is not None}
        
        if not audit_data.get('record_id'):
            logger.error("❌ Cannot create audit log without record_id (rfx_id/project_id)")
            return {}
        
        return self.insert_audit_log(audit_data)
    
    def get_rfx_history_events(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Legacy alias: get_rfx_history_events -> get_project_audit_events"""
        logger.warning("⚠️ get_rfx_history_events is deprecated, use get_project_audit_events instead")
        return self.get_project_audit_events(rfx_id)
    
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

# Legacy method aliases (only keep actively used methods)

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

def get_projects_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get projects history with pagination - modern schema compatible - OPTIMIZED WITH JOINS"""
    try:
        # SINGLE QUERY with JOINs - eliminates N+1 problem for history
        response = self.client.table("projects")\
            .select("*, organizations(*), users!created_by(*)")\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        projects = response.data or []
        
        # Build full name for user compatibility for each project
        for project in projects:
            if project.get('users'):
                user = project['users']
                first_name = user.get('first_name', '')
                last_name = user.get('last_name', '')
                user['name'] = f"{first_name} {last_name}".strip()
        
        logger.info(f"✅ Retrieved {len(projects)} projects history with related data in single query")
        return projects
        
    except Exception as e:
        logger.error(f"❌ Failed to get projects history: {e}")
        return []

def get_latest_rfx(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
    """Legacy alias: Get latest projects"""
    logger.warning("⚠️ get_latest_rfx called - requires organization context in new schema")
    return []

def get_rfx_products(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
    """Legacy alias: Project Items -> RFX Products with simple mapping"""
    try:
        items = self.get_project_items(rfx_id)
        # Simple mapping from project_items to rfx products format
        products = []
        for item in items:
            product = {
                'id': item.get('id'),
                'product_name': item.get('name', ''),
                'quantity': item.get('quantity', 1),
                'unit': item.get('unit', 'unidades'),
                'unit_price': item.get('unit_price', 0.0),
                'total_price': item.get('quantity', 1) * item.get('unit_price', 0.0),
                'specifications': item.get('description', ''),
                'category': item.get('category', 'general')
            }
            products.append(product)
        return products
    except Exception as e:
        logger.warning(f"⚠️ get_rfx_products failed for {rfx_id}: {e}")
        return []

def get_document_by_id(self, doc_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
    """Legacy alias: Quote -> Document with simple mapping"""
    try:
        quote = self.get_quote_by_id(doc_id)
        if quote:
            # Simple mapping from quote to document format
            document = {
                'id': quote.get('id'),
                'rfx_id': quote.get('project_id'),  # project_id -> rfx_id
                'title': quote.get('title', ''),
                'content_html': quote.get('html_content', ''),
                'total_amount': quote.get('total_amount', 0.0),
                'currency': quote.get('currency', 'USD'),
                'status': quote.get('status', 'generated'),
                'created_at': quote.get('created_at'),
                'updated_at': quote.get('updated_at'),
                'notes': quote.get('notes', ''),
                'metadata': quote.get('generation_data', {})
            }
            return document
    except Exception as e:
        logger.warning(f"⚠️ get_document_by_id failed for {doc_id}: {e}")
    return None

def get_proposals_by_rfx_id(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
    """Legacy alias: Get quotes for project with simple mapping"""
    try:
        quotes = self.get_quotes_by_project(rfx_id)
        documents = []
        for quote in quotes:
            # Use the same mapping as get_document_by_id
            document = {
                'id': quote.get('id'),
                'rfx_id': quote.get('project_id'),
                'title': quote.get('title', ''),
                'content_html': quote.get('html_content', ''),
                'total_amount': quote.get('total_amount', 0.0),
                'currency': quote.get('currency', 'USD'),
                'status': quote.get('status', 'generated'),
                'created_at': quote.get('created_at'),
                'updated_at': quote.get('updated_at'),
                'notes': quote.get('notes', ''),
                'metadata': quote.get('generation_data', {})
            }
            documents.append(document)
        return documents
    except Exception as e:
        logger.warning(f"⚠️ get_proposals_by_rfx_id failed for {rfx_id}: {e}")
        return []

def find_rfx_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
    """Legacy alias: Smart project lookup using modern method"""
    try:
        # For now, delegate to find_project_by_identifier if it exists, 
        # otherwise use get_project_by_id directly
        if hasattr(self, 'find_project_by_identifier'):
            project = self.find_project_by_identifier(identifier)
        else:
            # Fallback to direct ID lookup
            project = self.get_project_by_id(identifier)
        
        if project:
            # Use unified adapter to convert to RFX format
            from backend.adapters.unified_legacy_adapter import UnifiedLegacyAdapter
            adapter = UnifiedLegacyAdapter()
            return adapter.convert_to_format(project, 'rfx')
    except Exception as e:
        logger.warning(f"⚠️ find_rfx_by_identifier failed for {identifier}: {e}")
    return None

def update_rfx_status(self, rfx_id: Union[str, UUID], status: str) -> bool:
    """Legacy alias: Update project status"""
    return self.update_project_status(rfx_id, status)

# Add legacy methods to DatabaseClient (only actively used ones)
DatabaseClient.get_rfx_by_id = get_rfx_by_id
DatabaseClient.get_rfx_history = get_rfx_history
DatabaseClient.get_projects_history = get_projects_history
DatabaseClient.get_latest_rfx = get_latest_rfx
DatabaseClient.get_rfx_products = get_rfx_products
DatabaseClient.get_document_by_id = get_document_by_id
DatabaseClient.get_proposals_by_rfx_id = get_proposals_by_rfx_id
DatabaseClient.find_rfx_by_identifier = find_rfx_by_identifier
DatabaseClient.update_rfx_status = update_rfx_status

# ========================
# NEW BUDY AGENT METHODS
# ========================

def insert_project_context(self, project_id: Union[str, UUID], context_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert project context data (for BudyAgent) - modern schema only"""
    try:
        if 'id' not in context_data:
            context_data['id'] = str(uuid4())
        
        context_data['project_id'] = str(project_id)
        
        response = self.client.table("project_context").insert(context_data).execute()
        if response.data:
            logger.info(f"✅ Project context inserted for project: {project_id}")
            return response.data[0]
        else:
            raise Exception("No data returned from context insert")
    except Exception as e:
        logger.error(f"❌ Failed to insert project context: {e}")
        # Don't raise - this is not critical for functionality
        return {'id': str(uuid4()), 'project_id': str(project_id)}

def insert_workflow_state(self, state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert workflow state tracking - modern schema only"""
    try:
        if 'id' not in state_data:
            state_data['id'] = str(uuid4())
        
        response = self.client.table("workflow_states").insert(state_data).execute()
        if response.data:
            logger.info(f"✅ Workflow state inserted: {state_data.get('step_name')}")
            return response.data[0]
        else:
            raise Exception("No data returned from workflow state insert")
    except Exception as e:
        logger.error(f"❌ Failed to insert workflow state: {e}")
        # Don't raise - this is not critical for functionality
        return {'id': str(uuid4()), 'project_id': state_data.get('project_id')}

# Add new methods to DatabaseClient
DatabaseClient.insert_project_context = insert_project_context
DatabaseClient.insert_workflow_state = insert_workflow_state

def update_project_status(self, project_id: Union[str, UUID], status: str) -> bool:
    """Update project status"""
    try:
        if self._schema_mode == 'legacy':
            # Update legacy table
            response = self.client.table("rfx_v2")\
                .update({"status": status})\
                .eq("id", str(project_id))\
                .execute()
        else:
            # Update modern table
            response = self.client.table("projects")\
                .update({"status": status})\
                .eq("id", str(project_id))\
                .execute()
        
        if response.data:
            logger.info(f"✅ Project status updated to: {status}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Failed to update project status: {e}")
        return False

# Add new methods to DatabaseClient
DatabaseClient.insert_project_context = insert_project_context
DatabaseClient.insert_workflow_state = insert_workflow_state  
DatabaseClient.update_project_status = update_project_status

# Alias for backward compatibility
def get_supabase() -> Client:
    """Get raw Supabase client (for backward compatibility)"""
    return get_database_client().client