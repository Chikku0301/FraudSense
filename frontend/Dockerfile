FROM node:22-alpine

WORKDIR /app

# Copy dependency configs
COPY package*.json ./

# Install packages
RUN npm install

# Copy frontend codebase
COPY . .

EXPOSE 5173

# Vite server host bind
CMD ["npm", "run", "dev", "--", "--host"]
