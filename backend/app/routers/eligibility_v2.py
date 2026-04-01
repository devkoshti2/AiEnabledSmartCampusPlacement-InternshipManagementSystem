import sys

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.auth import get_current_active_user, require_admin
from app.database import get_db_connection
from app.ai.eligibility_predictor_v2 import EligibilityPredictorV2
import logging
import numpy as np
from typing import List, Optional
from datetime import datetime
import json

router = APIRouter(prefix="/eligibility", tags=["Eligibility Prediction V2"])
logger = logging.getLogger(__name__)

# Initialize predictor
predictor = EligibilityPredictorV2()

@router.post("/train")
async def train_model(
    background_tasks: BackgroundTasks,
    model_type: str = Query('xgboost', description="xgboost or lightgbm"),
    n_samples: int = Query(2000, description="Number of training samples"),
    admin = Depends(require_admin)
):
    """Train enhanced eligibility model with database logging"""
    
    try:
        # Start training in background
        background_tasks.add_task(
            train_model_task,
            model_type,
            n_samples,
            admin['id']
        )
        
        return {
            'message': 'Model training started in background',
            'status': 'training'
        }
        
    except Exception as e:
        logger.error(f"Training error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def train_model_task(model_type: str, admin_id: int, n_samples: int = 2000, log_id: int = None):
    """Background task for training eligibility model"""
    
    from app.database import get_db_connection
    import time
    import json
    import numpy as np
    from datetime import datetime
    
    # Force print to flush immediately
    import sys
# __builtins__ की जगह sys.stdout use करो
    print = lambda *args, **kwargs: sys.stdout.write(' '.join(map(str, args)) + '\n') and sys.stdout.flush()
    
    print("\n" + "="*70)
    print("🚀🚀🚀 TRAIN MODEL TASK STARTED 🚀🚀🚀")
    print(f"Model: {model_type}")
    print(f"Samples: {n_samples}")
    print(f"Admin ID: {admin_id}")
    print("="*70 + "\n")
    
    start_time = time.time()
    
    try:
        # ===== STEP 1: LOG TRAINING START (if log_id not provided) =====
        if not log_id:
            print("📝 Step 1: Logging training start...")
            conn = get_db_connection()
            if conn:
                print("✅ Database connected for training log")
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO training_logs (model_type, status, message, created_by)
                    VALUES (%s, 'started', %s, %s)
                """, ('eligibility', f"Training started with {n_samples} samples", admin_id))
                log_id = cursor.lastrowid
                print(f"✅ Training log inserted with ID: {log_id}")
                conn.commit()
                cursor.close()
                conn.close()
                print("✅ Training log connection closed")
        
        # ===== STEP 2: TRAIN MODEL =====
        print("\n🧠 Step 2: Training model...")
        results = predictor.train_model(model_type=model_type, n_samples=n_samples)
        training_time = int(time.time() - start_time)
        print(f"✅ Model training completed in {training_time} seconds")
        
        # ===== STEP 3: CONVERT RESULTS =====
        print("\n🔄 Step 3: Converting numpy values...")
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy(item) for item in obj]
            else:
                return obj
        
        converted = convert_numpy(results)
        print(f"✅ Results converted successfully")
        print(f"   Accuracy: {converted.get('accuracy', 0)}")
        print(f"   Precision: {converted.get('precision', 0)}")
        print(f"   Recall: {converted.get('recall', 0)}")
        print(f"   F1 Score: {converted.get('f1_score', 0)}")
        
        # ===== STEP 4: SAVE TO DATABASE =====
        print("\n💾 Step 4: Saving to database...")
        conn = get_db_connection()
        if conn:
            print("✅ Database connected for model version")
            cursor = conn.cursor()
            
            # Set old versions to not current
            print("   → Updating previous versions...")
            cursor.execute("""
                UPDATE model_versions 
                SET is_current = FALSE 
                WHERE model_type = 'eligibility'
            """)
            updated = cursor.rowcount
            print(f"   ✅ Updated {updated} previous versions")
            
            # Insert new version
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            metrics_json = json.dumps({
                'feature_importance': converted.get('feature_importance', {}),
                'model_type': model_type,
                'classes': converted.get('classes', [])
            })
            print(f"   → Inserting new version: {version}")
            
            cursor.execute("""
                INSERT INTO model_versions 
                (model_type, version, accuracy, precision_score, recall_score, f1_score_value, samples, 
                 is_current, created_by, training_time, metrics)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, %s, %s, %s)
            """, (
                'eligibility',
                version,
                converted.get('accuracy', 0),
                converted.get('precision', 0),
                converted.get('recall', 0),
                converted.get('f1_score', 0),
                n_samples,
                admin_id,
                training_time,
                metrics_json
            ))
            version_id = cursor.lastrowid
            print(f"   ✅✅✅ NEW VERSION INSERTED! ID: {version_id}")
            
            # Update training log
            if log_id:
                print(f"   → Updating training log {log_id}...")
                cursor.execute("""
                    UPDATE training_logs 
                    SET status = 'completed', completed_at = NOW(), 
                        accuracy = %s, samples = %s, message = %s
                    WHERE id = %s
                """, (
                    converted.get('accuracy', 0),
                    n_samples,
                    f"Training completed in {training_time}s",
                    log_id
                ))
                print(f"   ✅ Training log {log_id} updated")
            
            # Commit all changes
            conn.commit()
            print("✅ All changes COMMITTED to database")
            
            cursor.close()
            conn.close()
            print("✅ Database connection closed")
            
        else:
            print("❌ FAILED: Database connection for model version")
            return
        
        print("\n" + "="*70)
        print("✅✅✅ TRAINING TASK COMPLETED SUCCESSFULLY ✅✅✅")
        print(f"Version: {version}")
        print(f"Version ID: {version_id}")
        print(f"Log ID: {log_id}")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌❌❌ ERROR IN TRAINING TASK: {e}")
        import traceback
        traceback.print_exc()


@router.post("/predict/{drive_id}")
async def predict_eligibility(
    drive_id: int,
    current_user = Depends(get_current_active_user)
):
    """Predict eligibility for current student"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get student profile
        cursor.execute("""
            SELECT sp.*, u.full_name 
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
            WHERE sp.user_id = %s
        """, (current_user['id'],))
        
        student = cursor.fetchone()
        if not student:
            raise HTTPException(status_code=404, detail="Student profile not found")
        
        # Get drive details
        cursor.execute("""
            SELECT pd.*, c.name as company_name 
            FROM placement_drives pd
            JOIN companies c ON pd.company_id = c.id
            WHERE pd.id = %s
        """, (drive_id,))
        
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        # Make prediction
        prediction = predictor.predict(student, drive)
        
        return {
            'student_name': student['full_name'],
            'company': drive['company_name'],
            'job_title': drive['job_title'],
            'prediction': prediction
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.post("/batch-predict/{drive_id}")
async def batch_predict(
    drive_id: int,
    admin = Depends(require_admin)
):
    """Predict eligibility for all students for a drive"""
    
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get drive details
        cursor.execute("SELECT * FROM placement_drives WHERE id = %s", (drive_id,))
        drive = cursor.fetchone()
        if not drive:
            raise HTTPException(status_code=404, detail="Drive not found")
        
        # Get all students with profiles
        cursor.execute("""
            SELECT u.id as user_id, u.full_name, sp.* 
            FROM student_profiles sp
            JOIN users u ON sp.user_id = u.id
        """)
        
        students = cursor.fetchall()
        
        # Batch predict
        results = predictor.predict_batch(students, drive)
        
        return {
            'drive_id': drive_id,
            'job_title': drive['job_title'],
            'total_students': len(results),
            'predictions': results
        }
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/model-info")
async def get_model_info(
    admin = Depends(require_admin)
):
    """Get model information and performance metrics"""
    
    if predictor.model is None:
        return {'status': 'not_trained'}
    
    return {
        'status': 'trained',
        'model_type': predictor.model_type,
        'classes': predictor.model.classes_.tolist() if predictor.model else [],
        'feature_names': predictor.feature_names
    }