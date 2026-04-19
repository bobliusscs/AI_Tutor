"""
TTS语音合成 API路由
提供PPT课件讲解语音合成接口
"""

import base64
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.learning_plan import Section, Chapter
from app.services.dashscope_tts_service import get_dashscope_tts_service as get_tts_service

logger = logging.getLogger(__name__)

router = APIRouter()


class SlidesAudioRequest(BaseModel):
    """幻灯片语音请求"""
    speaker: Optional[str] = None  # 音色，默认使用配置


class SlidesAudioResponse(BaseModel):
    """幻灯片语音响应"""
    success: bool
    section_id: int
    section_title: str = ""
    chapter_title: str = ""
    speaker: str = ""
    slide_count: int = 0
    slides: list = []
    error: str = ""


class SingleSlideAudioResponse(BaseModel):
    """单个幻灯片语音响应"""
    success: bool
    section_id: int
    slide_index: int
    title: str = ""
    notes: str = ""
    audio_base64: str = ""
    duration: float = 0.0
    skipped: bool = False
    error: str = ""


class TTSHealthResponse(BaseModel):
    """TTS健康检查响应"""
    available: bool
    model_loaded: bool = False
    speakers: list = []
    reason: str = ""


@router.get("/health", response_model=TTSHealthResponse)
async def tts_health_check():
    """检查CosyVoice TTS服务是否可用"""
    tts = get_tts_service()
    result = await tts.health_check()
    return TTSHealthResponse(**result)


@router.post("/slides-audio/{section_id}", response_model=SlidesAudioResponse)
async def get_slides_audio(
    section_id: int,
    request: SlidesAudioRequest = SlidesAudioRequest(),
    db: Session = Depends(get_db)
):
    """
    获取指定节PPT所有幻灯片的讲解语音

    从数据库读取section的ppt_content，提取每页notes字段，
    调用CosyVoice TTS服务合成语音，返回音频列表。
    """
    # 1. 查询Section
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail=f"节不存在: {section_id}")

    # 2. 检查PPT是否已生成
    if not section.ppt_generated or not section.ppt_content:
        return SlidesAudioResponse(
            success=False,
            section_id=section_id,
            section_title=section.title,
            error="该节尚未生成PPT内容，请先生成PPT"
        )

    # 3. 获取章标题
    chapter = db.query(Chapter).filter(Chapter.id == section.chapter_id).first()
    chapter_title = chapter.title if chapter else ""

    # 4. 获取ppt_content中的slides
    slides = section.ppt_content
    if not isinstance(slides, list) or len(slides) == 0:
        return SlidesAudioResponse(
            success=False,
            section_id=section_id,
            section_title=section.title,
            chapter_title=chapter_title,
            error="PPT内容为空"
        )

    # 5. 调用TTS服务合成语音
    tts = get_tts_service()
    speaker = request.speaker

    # 检查TTS服务可用性
    health = await tts.health_check()
    if not health.get("available"):
        reason = health.get("reason", "未知原因")
        return SlidesAudioResponse(
            success=False,
            section_id=section_id,
            section_title=section.title,
            chapter_title=chapter_title,
            error=f"TTS服务不可用: {reason}"
        )

    # 批量合成
    audio_results = await tts.synthesize_slides(slides, speaker)

    # 6. 构建返回数据
    speaker_used = speaker or "Cherry"
    result_slides = []
    for audio_info in audio_results:
        slide_data = {
            "index": audio_info.get("index", 0),
            "title": audio_info.get("title", ""),
            "notes": audio_info.get("notes", ""),
            "audio_base64": audio_info.get("audio_base64", ""),
            "duration": audio_info.get("duration", 0),
            "skipped": audio_info.get("skipped", False),
        }
        if audio_info.get("error"):
            slide_data["error"] = audio_info["error"]
        result_slides.append(slide_data)

    # 统计
    success_count = sum(1 for s in result_slides if s.get("audio_base64"))
    skipped_count = sum(1 for s in result_slides if s.get("skipped"))

    logger.info(
        f"幻灯片语音合成: section_id={section_id}, "
        f"共{len(slides)}页, 成功{success_count}, 跳过{skipped_count}"
    )

    return SlidesAudioResponse(
        success=True,
        section_id=section_id,
        section_title=section.title,
        chapter_title=chapter_title,
        speaker=speaker_used,
        slide_count=len(slides),
        slides=result_slides
    )


@router.get("/slide-audio/{section_id}/{slide_index}", response_model=SingleSlideAudioResponse)
async def get_single_slide_audio(
    section_id: int,
    slide_index: int,
    speaker: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取指定节PPT中指定幻灯片的讲解语音（用于实时播放模式）

    从数据库读取section的ppt_content，提取指定页的notes字段，
    调用TTS服务合成语音，返回单个音频。
    """
    # 1. 查询Section
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail=f"节不存在: {section_id}")

    # 2. 检查PPT是否已生成
    if not section.ppt_generated or not section.ppt_content:
        return SingleSlideAudioResponse(
            success=False,
            section_id=section_id,
            slide_index=slide_index,
            error="该节尚未生成PPT内容，请先生成PPT"
        )

    # 3. 获取ppt_content中的slides
    slides = section.ppt_content
    if not isinstance(slides, list) or len(slides) == 0:
        return SingleSlideAudioResponse(
            success=False,
            section_id=section_id,
            slide_index=slide_index,
            error="PPT内容为空"
        )

    # 4. 检查slide_index是否有效
    if slide_index < 0 or slide_index >= len(slides):
        return SingleSlideAudioResponse(
            success=False,
            section_id=section_id,
            slide_index=slide_index,
            error=f"幻灯片索引无效: {slide_index}"
        )

    # 5. 获取指定幻灯片
    slide = slides[slide_index]
    notes = slide.get("notes", "")
    title = slide.get("title", "")

    # 6. 如果没有讲稿，跳过合成
    if not notes or not notes.strip():
        return SingleSlideAudioResponse(
            success=True,
            section_id=section_id,
            slide_index=slide_index,
            title=title,
            notes=notes,
            skipped=True
        )

    # 7. 调用TTS服务合成语音
    tts = get_tts_service()
    speaker = speaker or tts.default_speaker

    # 检查TTS服务可用性
    health = await tts.health_check()
    if not health.get("available"):
        reason = health.get("reason", "未知原因")
        return SingleSlideAudioResponse(
            success=False,
            section_id=section_id,
            slide_index=slide_index,
            title=title,
            notes=notes,
            error=f"TTS服务不可用: {reason}"
        )

    # 合成单页语音
    result = await tts.synthesize(notes, speaker)

    logger.info(
        f"单个幻灯片语音合成: section_id={section_id}, slide_index={slide_index}, "
        f"success={result.get('success')}, duration={result.get('duration', 0):.2f}s"
    )

    return SingleSlideAudioResponse(
        success=result.get("success", False),
        section_id=section_id,
        slide_index=slide_index,
        title=title,
        notes=notes,
        audio_base64=result.get("audio_base64", ""),
        duration=result.get("duration", 0.0),
        skipped=not result.get("success", False) and not result.get("error"),
        error=result.get("error", "")
    )


class SynthesizeAllAudioResponse(BaseModel):
    """批量合成所有幻灯片语音响应"""
    success: bool
    section_id: int
    total_slides: int = 0
    synthesized_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    error: str = ""


@router.post("/synthesize-all/{section_id}")
async def synthesize_all_slides_audio_stream(
    section_id: int,
    speaker: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    为指定节PPT的所有幻灯片合成讲解语音（并行合成，SSE流式输出）
    
    使用并发控制并行合成多页语音，提升合成效率。
    """
    import json
    
    # 1. 查询Section
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail=f"节不存在: {section_id}")

    # 2. 检查PPT是否已生成
    if not section.ppt_generated or not section.ppt_content:
        error_data = json.dumps({"type": "error", "message": "该节尚未生成PPT内容"})
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )

    slides = section.ppt_content
    
    # 深拷贝 slides，确保可以安全修改
    import copy
    slides = copy.deepcopy(slides)
    
    if not isinstance(slides, list) or len(slides) == 0:
        error_data = json.dumps({"type": "error", "message": "PPT内容为空"})
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )

    tts = get_tts_service()
    speaker_used = speaker or "Cherry"
    
    # 计算音频文件保存目录: backend/app/uploads/audio/{section_id}/
    uploads_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
    audio_dir = uploads_dir / "audio" / str(section_id)
    
    # 3. 检查TTS服务可用性
    try:
        health = await tts.health_check()
        if not health.get("available"):
            error_data = json.dumps({"type": "error", "message": f"TTS服务不可用: {health.get('reason')}"})
            return StreamingResponse(
                iter([f"data: {error_data}\n\n"]),
                media_type="text/event-stream"
            )
    except Exception as e:
        error_data = json.dumps({"type": "error", "message": f"TTS服务连接失败: {str(e)}"})
        return StreamingResponse(
            iter([f"data: {error_data}\n\n"]),
            media_type="text/event-stream"
        )
    
    # 4. 并行生成器：使用信号量控制并发
    async def generate_progress():
        import asyncio
        
        total = len(slides)
        synthesized_count = 0
        skipped_count = 0
        failed_count = 0
        errors = []
        
        # 并发控制：最多同时合成3页（避免API速率限制）
        semaphore = asyncio.Semaphore(3)
        
        # 发送开始事件
        start_data = json.dumps({
            "type": "start",
            "total": total,
            "message": f"开始并行合成 {total} 页语音（并发数: 3）..."
        })
        yield f"data: {start_data}\n\n"
        
        logger.info(f"[synthesize_all] 开始并行合成: 节{section_id}, {total}页")
        
        async def process_slide(i, slide, retry_count=0, max_retries=2):
            """处理单个幻灯片的异步任务，支持重试"""
            async with semaphore:
                notes = slide.get("notes", "")
                title = slide.get("title", "")
                page_num = i + 1
                
                # 如果没有讲稿，跳过
                if not notes or not notes.strip():
                    return {
                        "type": "page_complete",
                        "page": page_num,
                        "title": title,
                        "status": "skipped",
                        "message": f"第 {page_num} 页跳过（无讲稿）"
                    }
                
                try:
                    # 调用TTS合成
                    result = await tts.synthesize(notes, speaker_used)
                    
                    if result.get("success"):
                        # 将音频base64解码保存为wav文件
                        audio_base64 = result.get("audio_base64", "")
                        if audio_base64:
                            try:
                                audio_dir.mkdir(parents=True, exist_ok=True)
                                audio_bytes = base64.b64decode(audio_base64)
                                audio_filename = f"slide_{i}.wav"
                                audio_filepath = audio_dir / audio_filename
                                with open(audio_filepath, "wb") as f:
                                    f.write(audio_bytes)
                                slide["audio_url"] = f"/uploads/audio/{section_id}/{audio_filename}"
                                logger.debug(f"[synthesize_all] 音频已保存到: {audio_filepath}")
                            except Exception as save_err:
                                logger.error(f"[synthesize_all] 保存音频文件失败: {save_err}")
                                slide["audio_url"] = ""
                        else:
                            slide["audio_url"] = ""
                        slide["audio_duration"] = result.get("duration", 0.0)
                        slide.pop("audio_base64", None)
                        
                        return {
                            "type": "page_complete",
                            "page": page_num,
                            "title": title,
                            "status": "success",
                            "duration": result.get("duration", 0),
                            "message": f"第 {page_num} 页合成成功 ({result.get('duration', 0):.1f}s)"
                        }
                    else:
                        error_msg = result.get("error", "未知错误")
                        
                        # 如果是速率限制错误，且还有重试次数，等待后重试
                        if "rate limit" in error_msg.lower() and retry_count < max_retries:
                            wait_time = (retry_count + 1) * 2  # 递增等待时间
                            logger.warning(f"[synthesize_all] 第 {page_num} 页遇到速率限制，{wait_time}秒后重试 ({retry_count + 1}/{max_retries})")
                            await asyncio.sleep(wait_time)
                            return await process_slide(i, slide, retry_count + 1, max_retries)
                        
                        return {
                            "type": "page_complete",
                            "page": page_num,
                            "title": title,
                            "status": "failed",
                            "error": error_msg,
                            "message": f"第 {page_num} 页失败: {error_msg}"
                        }
                except Exception as e:
                    error_msg = str(e)
                    
                    # 如果是速率限制错误，且还有重试次数，等待后重试
                    if "rate limit" in error_msg.lower() and retry_count < max_retries:
                        wait_time = (retry_count + 1) * 2
                        logger.warning(f"[synthesize_all] 第 {page_num} 页遇到速率限制异常，{wait_time}秒后重试 ({retry_count + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        return await process_slide(i, slide, retry_count + 1, max_retries)
                    
                    return {
                        "type": "page_complete",
                        "page": page_num,
                        "title": title,
                        "status": "failed",
                        "error": error_msg,
                        "message": f"第 {page_num} 页异常: {error_msg}"
                    }
        
        # 创建所有任务
        tasks = [process_slide(i, slide) for i, slide in enumerate(slides)]
        
        # 使用 asyncio.as_completed 按完成顺序处理结果
        pending = set(asyncio.create_task(t) for t in tasks)
        
        # 记录已完成的数量，用于计算进度
        completed_results = {}
        
        while pending:
            # 等待任意一个任务完成
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                result = task.result()
                completed_results[result["page"]] = result
                
                # 发送 page_complete 事件（前端用于统计）
                page_data = json.dumps({
                    "type": "page_complete",
                    "page": len(completed_results),
                    "total": total,
                    "status": result["status"],
                    "message": result["message"]
                })
                yield f"data: {page_data}\n\n"
                
                # 统计结果
                if result["status"] == "success":
                    synthesized_count += 1
                    logger.info(f"[synthesize_all] 合成成功: section={section_id}, slide={result['page']}")
                elif result["status"] == "skipped":
                    skipped_count += 1
                elif result["status"] == "failed":
                    failed_count += 1
                    errors.append(f"第{result['page']}页: {result.get('error', '未知错误')}")
                    logger.warning(f"[synthesize_all] 合成失败: slide={result['page']}, error={result.get('error')}")
        
        # 最终保存（深拷贝 slides，flag_modified 确保 SQLAlchemy 检测到更改）
        import copy
        try:
            # 创建深拷贝
            slides_copy = copy.deepcopy(slides)
            # 显式标记为已修改
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(section, 'ppt_content')
            section.ppt_content = slides_copy
            db.commit()
            logger.info(f"[synthesize_all] 最终保存完成: section={section_id}")
            # 验证保存结果
            db.refresh(section)
            logger.info(f"[synthesize_all] 验证: 第一页是否有 audio_url = {section.ppt_content[0].get('audio_url') if section.ppt_content else 'N/A'}")
        except Exception as db_err:
            logger.error(f"[synthesize_all] 最终保存失败: {db_err}")
        
        # 发送完成事件
        final_data = json.dumps({
            "type": "complete",
            "total": total,
            "synthesized_count": synthesized_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "errors": errors[:3],
            "message": f"合成完成！成功 {synthesized_count} 页，跳过 {skipped_count} 页，失败 {failed_count} 页"
        })
        yield f"data: {final_data}\n\n"
        
        logger.info(
            f"[synthesize_all] 合成完成: section={section_id}, "
            f"total={total}, success={synthesized_count}, skipped={skipped_count}, failed={failed_count}"
        )
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
