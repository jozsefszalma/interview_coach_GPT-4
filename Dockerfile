FROM python:3.9
ENV KEY=""
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py /app/
EXPOSE 7860
CMD ["python", "bot.py"]