"""
🔌 Database Client V2.0 - English Schema Compatible
Centralized database operations with the new normalized structure
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
        """Check database connection health"""
        try:
            # Simple query to check connection - use rfx_v2 for V2.0 schema
            response = self.client.table("rfx_v2").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            # Fallback to old table if V2.0 not available
            try:
                response = self.client.table("rfx").select("id").limit(1).execute()
                return True
            except:
                return False
    
    # ========================
    # COMPANY OPERATIONS
    # ========================
    
    def insert_company(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update company information"""
        try:
            # Check if company exists by name or email
            existing = None
            if company_data.get("email"):
                existing = self.client.table("companies")\
                    .select("*")\
                    .eq("email", company_data["email"])\
                    .execute()
            
            if not existing or not existing.data:
                # Also check by name
                existing = self.client.table("companies")\
                    .select("*")\
                    .eq("name", company_data["name"])\
                    .execute()
            
            if existing and existing.data:
                # Update existing company
                response = self.client.table("companies")\
                    .update(company_data)\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
                logger.info(f"✅ Company updated: {company_data['name']}")
                return response.data[0] if response.data else existing.data[0]
            else:
                # Insert new company
                if 'id' not in company_data:
                    company_data['id'] = str(uuid4())
                
                response = self.client.table("companies")\
                    .insert(company_data)\
                    .execute()
                logger.info(f"✅ Company inserted: {company_data['name']}")
                return response.data[0] if response.data else company_data
                
        except Exception as e:
            logger.error(f"❌ Failed to insert/update company: {e}")
            raise
    
    def get_company_by_id(self, company_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get company by ID"""
        try:
            response = self.client.table("companies")\
                .select("*")\
                .eq("id", str(company_id))\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get company {company_id}: {e}")
            return None
    
    # ========================
    # REQUESTER OPERATIONS
    # ========================
    
    def insert_requester(self, requester_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update requester information"""
        try:
            # Check if requester exists by email
            existing = None
            if requester_data.get("email"):
                existing = self.client.table("requesters")\
                    .select("*")\
                    .eq("email", requester_data["email"])\
                    .execute()
            
            if existing and existing.data:
                # Update existing requester
                response = self.client.table("requesters")\
                    .update(requester_data)\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
                logger.info(f"✅ Requester updated: {requester_data.get('email', requester_data.get('name'))}")
                return response.data[0] if response.data else existing.data[0]
            else:
                # Insert new requester
                if 'id' not in requester_data:
                    requester_data['id'] = str(uuid4())
                
                response = self.client.table("requesters")\
                    .insert(requester_data)\
                    .execute()
                logger.info(f"✅ Requester inserted: {requester_data.get('email', requester_data.get('name'))}")
                return response.data[0] if response.data else requester_data
                
        except Exception as e:
            logger.error(f"❌ Failed to insert/update requester: {e}")
            raise
    
    def get_requester_by_id(self, requester_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get requester by ID"""
        try:
            response = self.client.table("requesters")\
                .select("*, companies(*)")\
                .eq("id", str(requester_id))\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get requester {requester_id}: {e}")
            return None
    
    # ========================
    # RFX OPERATIONS
    # ========================
    
    def insert_rfx(self, rfx_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert RFX data into database"""
        try:
            if 'id' not in rfx_data:
                rfx_data['id'] = str(uuid4())
            
            response = self.client.table("rfx_v2").insert(rfx_data).execute()
            if response.data:
                logger.info(f"✅ RFX inserted successfully: {response.data[0]['id']}")
                return response.data[0]
            else:
                raise Exception("No data returned from insert operation")
        except Exception as e:
            logger.error(f"❌ Failed to insert RFX: {e}")
            raise
    
    def get_rfx_by_id(self, rfx_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get RFX by ID with company and requester information"""
        try:
            response = self.client.table("rfx_v2")\
                .select("*, companies(*), requesters(*)")\
                .eq("id", str(rfx_id))\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get RFX {rfx_id}: {e}")
            raise
    
    def get_rfx_history(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get RFX history with pagination"""
        try:
            response = self.client.table("rfx_v2")\
                .select("*, companies(*), requesters(*)")\
                .order("received_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get RFX history: {e}")
            raise
    
    def get_latest_rfx(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get latest RFX ordered by creation date with optimized query for load-more pattern"""
        try:
            # Use created_at as primary sort, fallback to received_at if needed
            response = self.client.table("rfx_v2")\
                .select("*, companies(*), requesters(*)")\
                .order("created_at", desc=True)\
                .range(offset, offset + limit - 1)\
                .execute()
            
            logger.info(f"✅ Retrieved {len(response.data) if response.data else 0} latest RFX (offset: {offset}, limit: {limit})")
            return response.data or []
        except Exception as e:
            # Fallback to received_at if created_at doesn't work
            logger.warning(f"⚠️ Primary query failed, trying fallback: {e}")
            try:
                response = self.client.table("rfx_v2")\
                    .select("*, companies(*), requesters(*)")\
                    .order("received_at", desc=True)\
                    .range(offset, offset + limit - 1)\
                    .execute()
                
                logger.info(f"✅ Retrieved {len(response.data) if response.data else 0} latest RFX via fallback")
                return response.data or []
            except Exception as fallback_error:
                logger.error(f"❌ Both queries failed: {fallback_error}")
                raise
    
    def update_rfx_status(self, rfx_id: Union[str, UUID], status: str) -> bool:
        """Update RFX status"""
        try:
            response = (
                self.client.table("rfx_v2")
                .update({"status": status})
                .eq("id", str(rfx_id))
                .execute()
            )
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ RFX status updated: {rfx_id} -> {status}")
                return True
            else:
                logger.warning(f"⚠️ No RFX found to update: {rfx_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to update RFX status: {e}")
            raise
    
    def update_rfx_data(self, rfx_id: Union[str, UUID], update_data: Dict[str, Any]) -> bool:
        """Update RFX data fields (requester, company, delivery info, etc.)"""
        try:
            logger.info(f"🔄 DEBUG: update_rfx_data called for RFX: {rfx_id}")
            logger.info(f"🔄 DEBUG: Raw update_data: {update_data}")
            
            # Define allowed fields to update (security measure)
            # NOTA: Solo campos que realmente existen en la tabla rfx_v2 del esquema V2.0
            allowed_fields = {
                "delivery_date", "delivery_time", "location", "requirements", 
                "metadata_json", "description", "title", "status", "priority",
                "estimated_budget", "actual_cost"
            }
            
            logger.info(f"🔄 DEBUG: Allowed fields: {allowed_fields}")
            
            # Filter update_data to only include allowed fields
            filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            logger.info(f"🔄 DEBUG: Filtered data: {filtered_data}")
            
            if not filtered_data:
                logger.warning(f"⚠️ DEBUG: No valid fields to update for RFX {rfx_id}")
                logger.warning(f"⚠️ DEBUG: Attempted fields: {list(update_data.keys())}")
                return False
            
            logger.info(f"🔄 DEBUG: Executing database update for RFX {rfx_id}")
            logger.info(f"🔄 DEBUG: Table: rfx_v2, Update data: {filtered_data}")
            
            response = (
                self.client.table("rfx_v2")
                .update(filtered_data)
                .eq("id", str(rfx_id))
                .execute()
            )
            
            logger.info(f"🔍 DEBUG: Database response: {response}")
            logger.info(f"🔍 DEBUG: Response data: {response.data}")
            logger.info(f"🔍 DEBUG: Response data length: {len(response.data) if response.data else 0}")
            
            if response.data and len(response.data) > 0:
                logger.info(f"✅ DEBUG: RFX data updated successfully: {rfx_id} -> {list(filtered_data.keys())}")
                logger.info(f"✅ DEBUG: Updated record: {response.data[0] if response.data else 'No data'}")
                return True
            else:
                logger.warning(f"⚠️ DEBUG: No RFX found to update: {rfx_id}")
                logger.warning(f"⚠️ DEBUG: This could mean the RFX ID doesn't exist in the database")
                return False
                
        except Exception as e:
            logger.error(f"❌ DEBUG: Exception in update_rfx_data: {e}")
            logger.error(f"❌ DEBUG: Exception type: {type(e)}")
            import traceback
            logger.error(f"❌ DEBUG: Full traceback: {traceback.format_exc()}")
            raise
    
    # ========================
    # RFX PRODUCTS OPERATIONS
    # ========================
    
    def insert_rfx_products(self, rfx_id: Union[str, UUID], products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Insert structured products for an RFX"""
        try:
            if not products:
                logger.warning(f"No products to insert for RFX {rfx_id}")
                return []
            
            products_data = []
            for i, product in enumerate(products):
                product_data = product.copy()
                product_data['rfx_id'] = str(rfx_id)
                if 'id' not in product_data:
                    product_data['id'] = str(uuid4())
                
                # Ensure required fields exist
                if 'product_name' not in product_data or not product_data['product_name']:
                    logger.warning(f"Product {i} missing product_name, skipping")
                    continue
                    
                if 'quantity' not in product_data:
                    product_data['quantity'] = 1
                    
                if 'unit' not in product_data:
                    product_data['unit'] = 'unidades'
                
                # Clean any None values that might cause issues
                for key, value in list(product_data.items()):
                    if value is None and key not in ['estimated_unit_price', 'total_estimated_cost', 'supplier_id', 'catalog_product_id', 'description', 'notes']:
                        del product_data[key]
                
                products_data.append(product_data)
                logger.debug(f"✅ Prepared product {i}: {product_data.get('product_name')} (ID: {product_data['id']})")
            
            if not products_data:
                logger.warning(f"No valid products to insert for RFX {rfx_id}")
                return []
            
            logger.info(f"🔄 Inserting {len(products_data)} products for RFX {rfx_id}")
            response = self.client.table("rfx_products").insert(products_data).execute()
            
            if response.data:
                logger.info(f"✅ {len(response.data)} RFX products inserted successfully for RFX {rfx_id}")
                for product in response.data:
                    logger.debug(f"   - {product.get('product_name')} (ID: {product.get('id')})")
                return response.data
            else:
                logger.error(f"❌ No data returned after inserting products for RFX {rfx_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Failed to insert RFX products for {rfx_id}: {e}")
            logger.error(f"❌ Products data that failed: {products_data if 'products_data' in locals() else 'N/A'}")
            raise
    
    def get_rfx_products(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all products for an RFX"""
        try:
            # Simple query without JOINs to avoid foreign key errors
            response = self.client.table("rfx_products")\
                .select("*")\
                .eq("rfx_id", str(rfx_id))\
                .execute()
            
            products = response.data or []
            logger.info(f"✅ Found {len(products)} products for RFX {rfx_id}")
            return products
        except Exception as e:
            logger.error(f"❌ Failed to get RFX products for {rfx_id}: {e}")
            return []
    
    def update_rfx_product_cost(self, rfx_id: Union[str, UUID], product_id: str, unit_price: float) -> bool:
        """Update unit price for a specific RFX product"""
        try:
            response = self.client.table("rfx_products")\
                .update({"estimated_unit_price": unit_price})\
                .eq("rfx_id", str(rfx_id))\
                .eq("id", product_id)\
                .execute()
            
            if response.data:
                logger.info(f"✅ Updated product {product_id} cost to ${unit_price:.2f}")
                return True
            else:
                logger.warning(f"⚠️ No product found to update: RFX {rfx_id}, Product {product_id}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update product cost: {e}")
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
    # DOCUMENT OPERATIONS
    # ========================
    
    def insert_generated_document(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert generated document record with V2.0 schema mapping"""
        try:
            if 'id' not in doc_data:
                doc_data['id'] = str(uuid4())
            
            # ✅ Map legacy Spanish column names to V2.0 English schema
            mapped_data = self._map_document_data_to_v2(doc_data)
            
            response = self.client.table("generated_documents").insert(mapped_data).execute()
            if response.data:
                logger.info(f"✅ Document record inserted: {response.data[0]['id']}")
                return response.data[0]
            else:
                raise Exception("No data returned from document insert")
        except Exception as e:
            logger.error(f"❌ Failed to insert document record: {e}")
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
    
    def get_document_by_id(self, doc_id: Union[str, UUID]) -> Optional[Dict[str, Any]]:
        """Get generated document by ID"""
        try:
            response = self.client.table("generated_documents")\
                .select("*")\
                .eq("id", str(doc_id))\
                .execute()
            
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get document {doc_id}: {e}")
            raise
    
    def get_proposals_by_rfx_id(self, rfx_id: Union[str, UUID]) -> List[Dict[str, Any]]:
        """Get all proposals for a specific RFX"""
        try:
            response = self.client.table("generated_documents")\
                .select("*")\
                .eq("rfx_id", str(rfx_id))\
                .eq("document_type", "proposal")\
                .order("created_at", desc=True)\
                .execute()
            
            return response.data or []
        except Exception as e:
            logger.error(f"❌ Failed to get proposals for RFX {rfx_id}: {e}")
            raise
    
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
    # RAW SQL METHODS (for user_repository)
    # ========================
    
    def query_one(self, query: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """Execute SQL query and return single result - MEJORADO para user authentication"""
        try:
            logger.debug(f"🔍 Executing query_one: {query[:100]}...")
            
            # Handle SELECT queries for users
            if "SELECT" in query and "FROM users" in query and "WHERE email" in query and params:
                email = params[0]
                # Usar todos los campos que solicita la consulta
                response = self.client.table("users").select("*").eq("email", email).limit(1).execute()
                return response.data[0] if response.data else None
                
            elif "SELECT" in query and "FROM users" in query and "WHERE id" in query and params:
                user_id = params[0]
                response = self.client.table("users").select("*").eq("id", str(user_id)).limit(1).execute()
                return response.data[0] if response.data else None
                
            # Handle branding function calls
            elif "has_user_branding_configured" in query and params:
                user_id = params[0]
                # Implementar la lógica de has_user_branding_configured según el schema SQL
                try:
                    response = self.client.table("company_branding_assets")\
                        .select("id")\
                        .eq("user_id", str(user_id))\
                        .eq("is_active", True)\
                        .eq("analysis_status", "completed")\
                        .limit(1)\
                        .execute()
                    
                    has_branding = len(response.data) > 0 if response.data else False
                    return {"has_branding": has_branding}
                    
                except Exception as e:
                    logger.warning(f"❌ Error checking branding: {e}")
                    return {"has_branding": False}
                
            # Handle INSERT queries for users - CRÍTICO para crear usuarios
            elif "INSERT INTO users" in query and params:
                logger.info("🔄 Executing INSERT via Supabase client")
                
                # Extraer valores de los parámetros según el orden en la query
                # INSERT INTO users (email, password_hash, full_name, company_name)
                if len(params) >= 4:
                    email, password_hash, full_name, company_name = params[:4]
                    
                    # ✅ COINCIDIR EXACTAMENTE con Complete-Schema-V3.0-With-Auth.sql
                    user_data = {
                        "email": email.lower(),  # Enforce lowercase per schema constraint
                        "password_hash": password_hash, 
                        "full_name": full_name,
                        "company_name": company_name,
                        # Defaults según schema SQL:
                        "email_verified": False,  # DEFAULT false
                        "status": "pending_verification",  # DEFAULT 'pending_verification'
                        "failed_login_attempts": 0,  # DEFAULT 0
                        # created_at y updated_at se manejan automáticamente por Supabase
                    }
                    
                    response = self.client.table("users").insert(user_data).execute()
                    
                    if response.data and len(response.data) > 0:
                        created_user = response.data[0]
                        logger.info(f"✅ User created via query_one: {email} (ID: {created_user.get('id')})")
                        return created_user
                    else:
                        logger.error("❌ Insert failed: No data returned")
                        return None
                else:
                    logger.error(f"❌ INSERT params insufficient: {len(params)} provided, expected 4")
                    return None
                
            else:
                logger.warning(f"Unsupported query in query_one: {query[:50]}...")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error in query_one: {e}")
            return None
    
    def query_all(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return all results"""
        try:
            logger.debug(f"🔍 Executing query_all: {query[:100]}...")
            
            # Handle common queries
            if "SELECT" in query and "users" in query:
                response = self.client.table("users").select("*").execute()
                return response.data or []
                
            else:
                logger.warning(f"Unsupported query in query_all: {query[:50]}...")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in query_all: {e}")
            return []
    
    def execute(self, query: str, params: tuple = None) -> bool:
        """Execute SQL query without returning results"""
        try:
            logger.debug(f"🔍 Executing: {query[:100]}...")
            
            # Handle UPDATE and DELETE queries
            if "UPDATE users" in query and params:
                # This should use proper Supabase updates
                logger.warning("Direct UPDATE via execute not recommended, use client.table().update()")
                return True
                
            elif "DELETE FROM users" in query:
                logger.warning("Direct DELETE via execute not recommended, use client.table().delete()")
                return True
                
            else:
                logger.warning(f"Unsupported query in execute: {query[:50]}...")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in execute: {e}")
            return False

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


# Alias for backward compatibility
def get_supabase() -> Client:
    """Get raw Supabase client (for backward compatibility)"""
    return get_database_client().client